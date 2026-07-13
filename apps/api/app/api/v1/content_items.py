from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.api.v1.audience_segments import get_audience_segment_in_organization_brand
from app.api.v1.brand_lifecycle import ensure_brand_content_writable
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.content_versions import create_content_version_record, next_content_version_number
from app.api.v1.jobs import _job_read
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.enums import GenerationType
from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.job import Job
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.db.session import get_db
from app.domain.content_generation import (
    build_content_generation_brief_content,
    build_content_generation_brief_title,
    build_content_generation_job_title,
)
from app.domain.content_scope import ContentScope
from app.schemas.content_item import ContentItemCreate, ContentItemListResponse, ContentItemRead
from app.schemas.job import JobRead
from app.schemas.ticket import ContentItemReviewActionRequest, TicketRead

router = APIRouter(prefix='/content-items', tags=['content-items'])


def get_content_item_in_organization_brand(db: Session, content_item_id: UUID, organization_id: UUID, brand_id: UUID) -> ContentItem:
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    if content_item.organization_id != organization_id or content_item.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content item does not belong to organization and brand')
    return content_item


def _create_review_ticket(
    *,
    db: Session,
    current_user: User,
    content_item: ContentItem,
    ticket_type: str,
    ticket_status: str,
    reason_codes: list[str] | None,
    comment: str | None,
    priority: str,
    assigned_agent_role: str,
    resolved_at: datetime | None = None,
) -> Ticket:
    content_version_id = content_item.current_version_id
    if content_version_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content item has no current version')
    ticket = Ticket(
        organization_id=content_item.organization_id,
        brand_id=content_item.brand_id,
        product_id=content_item.product_id,
        content_item_id=content_item.id,
        content_version_id=content_version_id,
        type=ticket_type,
        reason_codes=reason_codes or [],
        comment=comment,
        status=ticket_status,
        priority=priority,
        assigned_agent_role=assigned_agent_role,
        created_by_id=current_user.id,
        resolved_at=resolved_at,
    )
    db.add(ticket)
    return ticket


def _load_reviewable_content_item(db: Session, content_item_id: UUID, memberships: list[OrganizationMembership]) -> ContentItem:
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    require_organization_manager(content_item.organization_id, memberships)
    organization = db.get(Organization, content_item.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, content_item.brand_id, content_item.organization_id)
    return content_item


@router.get('', response_model=ContentItemListResponse)
def list_content_items(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    scope: ContentScope | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    content_plan_id: UUID | None = Query(default=None),
    audience_segment_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentItemListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    query = select(ContentItem).where(ContentItem.organization_id == organization_id, ContentItem.brand_id == brand_id)
    if scope is not None:
        query = query.where(ContentItem.scope == scope.value)
    if product_id is not None:
        query = query.where(ContentItem.product_id == product_id)
    if content_plan_id is not None:
        query = query.where(ContentItem.content_plan_id == content_plan_id)
    if audience_segment_id is not None:
        query = query.where(ContentItem.audience_segment_id == audience_segment_id)
    items = db.execute(query.order_by(ContentItem.created_at.asc())).scalars().all()
    return ContentItemListResponse(items=[ContentItemRead.model_validate(item, from_attributes=True) for item in items])


@router.post('', response_model=ContentItemRead, status_code=status.HTTP_201_CREATED)
def create_content_item(
    payload: ContentItemCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentItemRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)

    content_plan = db.get(ContentPlan, payload.content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content plan not found')
    if content_plan.organization_id != payload.organization_id or content_plan.brand_id != payload.brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content plan does not belong to organization and brand')

    if payload.product_id is not None:
        get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    if payload.audience_segment_id is not None:
        get_audience_segment_in_organization_brand(db, payload.audience_segment_id, payload.organization_id, payload.brand_id)

    content_item = ContentItem(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        content_plan_id=payload.content_plan_id,
        audience_segment_id=payload.audience_segment_id,
        scope=payload.scope.value,
        platform=payload.platform,
        content_type=payload.content_type,
        goal=payload.goal,
        title=payload.title,
        status=payload.status,
        quality_score=payload.quality_score,
    )
    db.add(content_item)
    db.commit()
    db.refresh(content_item)
    return ContentItemRead.model_validate(content_item, from_attributes=True)


@router.post('/{content_item_id}/generate', response_model=JobRead, status_code=status.HTTP_201_CREATED)
def generate_content_item(
    content_item_id: UUID,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    require_organization_manager(content_item.organization_id, memberships)
    organization = db.get(Organization, content_item.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    content_plan = db.get(ContentPlan, content_item.content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content plan not found')
    if content_plan.organization_id != content_item.organization_id or content_plan.brand_id != content_item.brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content plan does not belong to content item and organization')
    brand = get_brand_in_organization(db, content_item.brand_id, content_item.organization_id)
    ensure_brand_content_writable(brand)
    if content_item.product_id is not None:
        get_product_in_organization_brand(db, content_item.product_id, content_item.organization_id, content_item.brand_id)
    if content_item.audience_segment_id is not None:
        get_audience_segment_in_organization_brand(db, content_item.audience_segment_id, content_item.organization_id, content_item.brand_id)

    brief = Brief(
        organization_id=content_item.organization_id,
        brand_id=content_item.brand_id,
        title=build_content_generation_brief_title(content_item),
        content=build_content_generation_brief_content(db, content_item, content_plan),
    )
    db.add(brief)
    db.flush()
    job = Job(
        organization_id=content_item.organization_id,
        brand_id=content_item.brand_id,
        brief_id=brief.id,
        title=build_content_generation_job_title(content_item),
        status='queued',
        execution_profile='general_content',
        kind='content_generation',
        target_brand_id=content_item.brand_id,
        target_product_id=content_item.product_id,
        target_content_item_id=content_item.id,
    )
    db.add(job)
    content_item.status = 'generating'
    db.commit()
    db.refresh(job)
    return _job_read(db, job)


@router.get('/{content_item_id}', response_model=ContentItemRead)
def get_content_item(
    content_item_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentItemRead:
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    get_organization_membership(content_item.organization_id, memberships)
    return ContentItemRead.model_validate(content_item, from_attributes=True)


@router.post('/{content_item_id}/approve', response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def approve_content_item(
    content_item_id: UUID,
    payload: ContentItemReviewActionRequest,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketRead:
    content_item = _load_reviewable_content_item(db, content_item_id, memberships)
    content_item.status = 'approved'
    ticket = _create_review_ticket(
        db=db,
        current_user=current_user,
        content_item=content_item,
        ticket_type='approval',
        ticket_status='resolved',
        reason_codes=payload.reason_codes,
        comment=payload.comment,
        priority=payload.priority,
        assigned_agent_role='reviewer',
        resolved_at=datetime.now(timezone.utc),
    )
    db.commit()
    db.refresh(ticket)
    return TicketRead.model_validate(ticket, from_attributes=True)


@router.post('/{content_item_id}/reject', response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def reject_content_item(
    content_item_id: UUID,
    payload: ContentItemReviewActionRequest,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketRead:
    content_item = _load_reviewable_content_item(db, content_item_id, memberships)
    content_item.status = 'rejected'
    ticket = _create_review_ticket(
        db=db,
        current_user=current_user,
        content_item=content_item,
        ticket_type='rejection',
        ticket_status='open',
        reason_codes=payload.reason_codes,
        comment=payload.comment,
        priority=payload.priority,
        assigned_agent_role=payload.assigned_agent_role,
    )
    db.commit()
    db.refresh(ticket)
    return TicketRead.model_validate(ticket, from_attributes=True)


@router.post('/{content_item_id}/request-revision', response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def request_content_item_revision(
    content_item_id: UUID,
    payload: ContentItemReviewActionRequest,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketRead:
    content_item = _load_reviewable_content_item(db, content_item_id, memberships)
    content_item.status = 'revision_requested'
    ticket = _create_review_ticket(
        db=db,
        current_user=current_user,
        content_item=content_item,
        ticket_type='revision_request',
        ticket_status='open',
        reason_codes=payload.reason_codes,
        comment=payload.comment,
        priority=payload.priority,
        assigned_agent_role=payload.assigned_agent_role,
    )
    db.commit()
    db.refresh(ticket)
    return TicketRead.model_validate(ticket, from_attributes=True)
