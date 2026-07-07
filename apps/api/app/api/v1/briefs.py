from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.brand_lifecycle import ensure_brand_content_writable
from app.api.v1.organizations import ensure_content_organization_writable
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import Organization, OrganizationMembership
from app.db.session import get_db
from app.schemas.brief import BriefCreate, BriefListResponse, BriefRead

router = APIRouter(prefix="/briefs", tags=["briefs"])


def get_brand_in_organization(db: Session, brand_id: UUID, organization_id: UUID) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    if brand.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brand does not belong to organization")
    return brand


@router.get("", response_model=BriefListResponse)
def list_briefs(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BriefListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    items = db.execute(
        select(Brief)
        .where(Brief.organization_id == organization_id, Brief.brand_id == brand_id)
        .order_by(Brief.created_at.asc())
    ).scalars().all()
    return BriefListResponse(items=[BriefRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=BriefRead, status_code=status.HTTP_201_CREATED)
def create_brief(
    payload: BriefCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BriefRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)
    brief = Brief(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        title=payload.title,
        content=payload.content,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return BriefRead.model_validate(brief, from_attributes=True)


@router.get("/{brief_id}", response_model=BriefRead)
def get_brief(
    brief_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BriefRead:
    brief = db.get(Brief, brief_id)
    if brief is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brief not found")
    get_organization_membership(brief.organization_id, memberships)
    return BriefRead.model_validate(brief, from_attributes=True)
