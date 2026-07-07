from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.api.v1.content_items import get_content_item_in_organization_brand
from app.api.v1.jobs import _job_read
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.content_version import ContentVersion
from app.db.models.job import Job
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.db.session import get_db
from app.domain.ticket_processing import (
    build_ticket_processing_brief_content,
    build_ticket_processing_brief_title,
    build_ticket_processing_job_title,
)
from app.schemas.ticket import TicketCreate, TicketListResponse, TicketRead
from app.schemas.job import JobRead

router = APIRouter(prefix='/tickets', tags=['tickets'])


def _validate_ticket_parent_scope(db: Session, payload: TicketCreate) -> tuple[ContentItem, ContentVersion | None]:
    content_item = get_content_item_in_organization_brand(db, payload.content_item_id, payload.organization_id, payload.brand_id)
    if payload.product_id is not None:
        get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    if payload.content_version_id is not None:
        content_version = db.get(ContentVersion, payload.content_version_id)
        if content_version is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content version not found')
        if content_version.organization_id != payload.organization_id or content_version.content_item_id != payload.content_item_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content version does not belong to content item and organization')
    else:
        content_version = None
    return content_item, content_version


@router.get('', response_model=TicketListResponse)
def list_tickets(
    organization_id: UUID = Query(...),
    content_item_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketListResponse:
    get_organization_membership(organization_id, memberships)
    query = select(Ticket).where(Ticket.organization_id == organization_id)
    if content_item_id is not None:
        query = query.where(Ticket.content_item_id == content_item_id)
    items = db.execute(query.order_by(Ticket.created_at.asc())).scalars().all()
    return TicketListResponse(items=[TicketRead.model_validate(item, from_attributes=True) for item in items])


@router.get('/{ticket_id}', response_model=TicketRead)
def get_ticket(
    ticket_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketRead:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found')
    get_organization_membership(ticket.organization_id, memberships)
    return TicketRead.model_validate(ticket, from_attributes=True)


@router.post('', response_model=TicketRead, status_code=status.HTTP_201_CREATED)
def create_ticket(
    payload: TicketCreate,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> TicketRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    _, content_version = _validate_ticket_parent_scope(db, payload)
    ticket = Ticket(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        content_item_id=payload.content_item_id,
        content_version_id=payload.content_version_id if content_version is not None else None,
        type=payload.type,
        reason_codes=payload.reason_codes,
        comment=payload.comment,
        status=payload.status,
        priority=payload.priority,
        assigned_agent_role=payload.assigned_agent_role,
        created_by_id=current_user.id,
        resolved_at=payload.resolved_at,
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return TicketRead.model_validate(ticket, from_attributes=True)


@router.post('/{ticket_id}/process', response_model=JobRead, status_code=status.HTTP_201_CREATED)
def process_ticket(
    ticket_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    ticket = db.get(Ticket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found')
    require_organization_manager(ticket.organization_id, memberships)
    organization = db.get(Organization, ticket.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    if ticket.status != 'open':
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Ticket is not open')
    content_item = get_content_item_in_organization_brand(db, ticket.content_item_id, ticket.organization_id, ticket.brand_id)
    if ticket.content_version_id is None or content_item.current_version_id != ticket.content_version_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Ticket does not target the current content version')
    brief = Brief(
        organization_id=ticket.organization_id,
        brand_id=ticket.brand_id,
        title=build_ticket_processing_brief_title(ticket, content_item),
        content=build_ticket_processing_brief_content(ticket, content_item),
    )
    db.add(brief)
    db.flush()
    job = Job(
        organization_id=ticket.organization_id,
        brand_id=ticket.brand_id,
        brief_id=brief.id,
        title=build_ticket_processing_job_title(ticket, content_item),
        status='queued',
        execution_profile='general_content',
        kind='ticket_processing',
        target_brand_id=ticket.brand_id,
        target_product_id=ticket.product_id,
        target_content_item_id=content_item.id,
        target_ticket_id=ticket.id,
    )
    db.add(job)
    ticket.status = 'in_progress'
    db.commit()
    db.refresh(job)
    return _job_read(job)
