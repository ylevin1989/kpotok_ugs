from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.api.v1.organizations import ensure_content_organization_writable
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_version import ContentVersion
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.product import Product
from app.db.models.quality_check import QualityCheck
from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.db.session import get_db
from app.domain.quality_checking import QualityCheckEvaluation, evaluate_quality_check
from app.schemas.quality_check import QualityCheckCreate, QualityCheckListResponse, QualityCheckRead

router = APIRouter(tags=['quality-checks'])


def _resolve_content_version(
    db: Session,
    *,
    content_item: ContentItem,
    organization_id: UUID,
    payload: QualityCheckCreate,
    ticket: Ticket | None,
) -> ContentVersion:
    resolved_version_id = payload.content_version_id or (ticket.content_version_id if ticket is not None else None) or content_item.current_version_id
    if resolved_version_id is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content item has no current version to quality check')
    content_version = db.get(ContentVersion, resolved_version_id)
    if content_version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content version not found')
    if content_version.organization_id != organization_id or content_version.content_item_id != content_item.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content version does not belong to content item and organization')
    if payload.content_version_id is not None and ticket is not None and ticket.content_version_id is not None and ticket.content_version_id != payload.content_version_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Ticket does not belong to the requested content version')
    return content_version


def _resolve_ticket(
    db: Session,
    *,
    content_item: ContentItem,
    organization_id: UUID,
    payload: QualityCheckCreate,
) -> Ticket | None:
    if payload.ticket_id is None:
        return None
    ticket = db.get(Ticket, payload.ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Ticket not found')
    if ticket.organization_id != organization_id or ticket.content_item_id != content_item.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Ticket does not belong to content item and organization')
    return ticket


def create_quality_check_record(
    *,
    db: Session,
    content_item: ContentItem,
    organization_id: UUID,
    content_version: ContentVersion,
    current_user: User | None,
    ticket: Ticket | None,
    threshold: int = 80,
    generated_from_task_id: UUID | None = None,
    checked_at=None,
    summary: str | None = None,
    checks_json: dict | None = None,
    issues_json: list[str] | None = None,
    recommendations_json: list[str] | None = None,
) -> QualityCheck:
    brand = db.get(Brand, content_item.brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Brand not found')
    product = db.get(Product, content_item.product_id) if content_item.product_id is not None else None
    evaluation: QualityCheckEvaluation = evaluate_quality_check(
        content_item=content_item,
        content_version=content_version,
        brand=brand,
        product=product,
        ticket=ticket,
        threshold=threshold,
    )
    quality_check = QualityCheck(
        organization_id=organization_id,
        brand_id=content_item.brand_id,
        product_id=content_item.product_id,
        content_item_id=content_item.id,
        content_version_id=content_version.id,
        ticket_id=ticket.id if ticket is not None else None,
        score=evaluation.score,
        threshold=evaluation.threshold,
        status=evaluation.status,
        summary=summary or evaluation.summary,
        checks_json={**evaluation.checks_json, **(checks_json or {})},
        issues_json=[*evaluation.issues_json, *(issues_json or [])],
        recommendations_json=[*evaluation.recommendations_json, *(recommendations_json or [])],
        generated_from_task_id=generated_from_task_id,
        created_by_id=current_user.id if current_user is not None else None,
        checked_at=checked_at,
    )
    db.add(quality_check)
    content_item.quality_score = evaluation.score
    content_item.status = evaluation.content_status
    if checked_at is not None:
        quality_check.checked_at = checked_at
    db.flush()
    return quality_check


@router.get('/quality-checks', response_model=QualityCheckListResponse)
def list_quality_checks(
    organization_id: UUID = Query(...),
    content_item_id: UUID | None = Query(default=None),
    content_version_id: UUID | None = Query(default=None),
    ticket_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> QualityCheckListResponse:
    get_organization_membership(organization_id, memberships)
    query = select(QualityCheck).where(QualityCheck.organization_id == organization_id)
    if content_item_id is not None:
        query = query.where(QualityCheck.content_item_id == content_item_id)
    if content_version_id is not None:
        query = query.where(QualityCheck.content_version_id == content_version_id)
    if ticket_id is not None:
        query = query.where(QualityCheck.ticket_id == ticket_id)
    items = db.execute(query.order_by(QualityCheck.checked_at.desc(), QualityCheck.created_at.desc())).scalars().all()
    return QualityCheckListResponse(items=[QualityCheckRead.model_validate(item, from_attributes=True) for item in items])


@router.get('/quality-checks/{quality_check_id}', response_model=QualityCheckRead)
def get_quality_check(
    quality_check_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> QualityCheckRead:
    quality_check = db.get(QualityCheck, quality_check_id)
    if quality_check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Quality check not found')
    get_organization_membership(quality_check.organization_id, memberships)
    return QualityCheckRead.model_validate(quality_check, from_attributes=True)


@router.post('/content-items/{content_item_id}/quality-check', response_model=QualityCheckRead, status_code=status.HTTP_201_CREATED)
def create_quality_check(
    content_item_id: UUID,
    payload: QualityCheckCreate,
    current_user: User = Depends(get_current_user),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> QualityCheckRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    content_item = db.get(ContentItem, content_item_id)
    if content_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    if content_item.organization_id != payload.organization_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Content item does not belong to organization')
    ticket = _resolve_ticket(db, content_item=content_item, organization_id=payload.organization_id, payload=payload)
    content_version = _resolve_content_version(db, content_item=content_item, organization_id=payload.organization_id, payload=payload, ticket=ticket)
    quality_check = create_quality_check_record(
        db=db,
        content_item=content_item,
        organization_id=payload.organization_id,
        content_version=content_version,
        current_user=current_user,
        ticket=ticket,
        threshold=payload.threshold,
        generated_from_task_id=payload.generated_from_task_id,
        checked_at=payload.checked_at,
        summary=payload.summary,
        checks_json=payload.checks_json,
        issues_json=payload.issues_json,
        recommendations_json=payload.recommendations_json,
    )
    db.commit()
    db.refresh(quality_check)
    db.refresh(content_item)
    return QualityCheckRead.model_validate(quality_check, from_attributes=True)
