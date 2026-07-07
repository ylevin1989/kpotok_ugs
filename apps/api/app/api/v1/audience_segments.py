from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.brand_lifecycle import ensure_brand_content_writable
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.models.audience_segment import AudienceSegment
from app.db.models.organization import Organization, OrganizationMembership
from app.db.session import get_db
from app.domain.content_scope import ContentScope
from app.schemas.audience_segment import AudienceSegmentCreate, AudienceSegmentListResponse, AudienceSegmentRead

router = APIRouter(prefix="/audience-segments", tags=["audience-segments"])


def get_audience_segment_in_organization_brand(db: Session, audience_segment_id: UUID, organization_id: UUID, brand_id: UUID) -> AudienceSegment:
    audience_segment = db.get(AudienceSegment, audience_segment_id)
    if audience_segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience segment not found")
    if audience_segment.organization_id != organization_id or audience_segment.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Audience segment does not belong to organization and brand")
    return audience_segment


@router.get("", response_model=AudienceSegmentListResponse)
def list_audience_segments(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    scope: ContentScope | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> AudienceSegmentListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    query = select(AudienceSegment).where(AudienceSegment.organization_id == organization_id, AudienceSegment.brand_id == brand_id)
    if scope is not None:
        query = query.where(AudienceSegment.scope == scope.value)
    if product_id is not None:
        query = query.where(AudienceSegment.product_id == product_id)
    items = db.execute(query.order_by(AudienceSegment.created_at.asc())).scalars().all()
    return AudienceSegmentListResponse(items=[AudienceSegmentRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=AudienceSegmentRead, status_code=status.HTTP_201_CREATED)
def create_audience_segment(
    payload: AudienceSegmentCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> AudienceSegmentRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)
    if payload.product_id is not None:
        get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    audience_segment = AudienceSegment(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        scope=payload.scope.value,
        name=payload.name,
        description=payload.description,
        pain_points=payload.pain_points,
        goals=payload.goals,
        objections=payload.objections,
        keywords=payload.keywords,
    )
    db.add(audience_segment)
    db.commit()
    db.refresh(audience_segment)
    return AudienceSegmentRead.model_validate(audience_segment, from_attributes=True)


@router.get("/{audience_segment_id}", response_model=AudienceSegmentRead)
def get_audience_segment(
    audience_segment_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> AudienceSegmentRead:
    audience_segment = db.get(AudienceSegment, audience_segment_id)
    if audience_segment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Audience segment not found")
    get_organization_membership(audience_segment.organization_id, memberships)
    return AudienceSegmentRead.model_validate(audience_segment, from_attributes=True)
