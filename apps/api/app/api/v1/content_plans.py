from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.audience_segments import get_audience_segment_in_organization_brand
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.models.content_plan import ContentPlan
from app.db.models.organization import Organization, OrganizationMembership
from app.db.session import get_db
from app.domain.content_scope import ContentScope
from app.schemas.content_plan import ContentPlanCreate, ContentPlanListResponse, ContentPlanRead

router = APIRouter(prefix="/content-plans", tags=["content-plans"])


def get_content_plan_in_organization_brand(db: Session, content_plan_id: UUID, organization_id: UUID, brand_id: UUID) -> ContentPlan:
    content_plan = db.get(ContentPlan, content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content plan not found")
    if content_plan.organization_id != organization_id or content_plan.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Content plan does not belong to organization and brand")
    return content_plan


@router.get("", response_model=ContentPlanListResponse)
def list_content_plans(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    scope: ContentScope | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    audience_segment_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentPlanListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    query = select(ContentPlan).where(ContentPlan.organization_id == organization_id, ContentPlan.brand_id == brand_id)
    if scope is not None:
        query = query.where(ContentPlan.scope == scope.value)
    if product_id is not None:
        query = query.where(ContentPlan.product_id == product_id)
    if audience_segment_id is not None:
        query = query.where(ContentPlan.audience_segment_id == audience_segment_id)
    items = db.execute(query.order_by(ContentPlan.date.asc(), ContentPlan.created_at.asc())).scalars().all()
    return ContentPlanListResponse(items=[ContentPlanRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=ContentPlanRead, status_code=status.HTTP_201_CREATED)
def create_content_plan(
    payload: ContentPlanCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentPlanRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    if payload.product_id is not None:
        get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    if payload.audience_segment_id is not None:
        get_audience_segment_in_organization_brand(db, payload.audience_segment_id, payload.organization_id, payload.brand_id)
    content_plan = ContentPlan(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        audience_segment_id=payload.audience_segment_id,
        scope=payload.scope.value,
        date=payload.date,
        title=payload.title,
        platform=payload.platform,
        content_type=payload.content_type,
        goal=payload.goal,
        status=payload.status,
    )
    db.add(content_plan)
    db.commit()
    db.refresh(content_plan)
    return ContentPlanRead.model_validate(content_plan, from_attributes=True)


@router.get("/{content_plan_id}", response_model=ContentPlanRead)
def get_content_plan(
    content_plan_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentPlanRead:
    content_plan = db.get(ContentPlan, content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content plan not found")
    get_organization_membership(content_plan.organization_id, memberships)
    return ContentPlanRead.model_validate(content_plan, from_attributes=True)
