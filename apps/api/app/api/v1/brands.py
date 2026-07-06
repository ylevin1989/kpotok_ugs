from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.jobs import _job_read
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import Organization, OrganizationMembership, OrganizationStatus
from app.db.session import get_db
from app.domain.dna_generation import (
    build_brand_dna_brief_content,
    build_brand_dna_brief_title,
    build_brand_dna_job_title,
)
from app.schemas.brand import BrandCreate, BrandListResponse, BrandRead, BrandUpdate
from app.schemas.job import JobRead

router = APIRouter(prefix="/brands", tags=["brands"])


def ensure_brand_hard_delete_allowed(db: Session, brand: Brand) -> None:
    has_brief = db.execute(select(Brief.id).where(Brief.brand_id == brand.id).limit(1)).first() is not None
    has_job = db.execute(select(Job.id).where(Job.brand_id == brand.id).limit(1)).first() is not None
    if has_brief or has_job:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Brand with briefs or jobs cannot be hard-deleted",
        )


@router.get("", response_model=BrandListResponse)
def list_brands(
    organization_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BrandListResponse:
    get_organization_membership(organization_id, memberships)
    items = db.execute(
        select(Brand).where(Brand.organization_id == organization_id).order_by(Brand.created_at.asc())
    ).scalars().all()
    return BrandListResponse(items=[BrandRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=BrandRead, status_code=status.HTTP_201_CREATED)
def create_brand(
    payload: BrandCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BrandRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    brand = Brand(
        organization_id=payload.organization_id,
        name=payload.name,
        slug=payload.slug,
    )
    db.add(brand)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brand slug already exists in organization") from exc
    db.refresh(brand)
    return BrandRead.model_validate(brand, from_attributes=True)


@router.post("/{brand_id}/generate-dna", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def generate_brand_dna(
    brand_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    require_organization_manager(brand.organization_id, memberships)
    organization = db.get(Organization, brand.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    brief = Brief(
        organization_id=brand.organization_id,
        brand_id=brand.id,
        title=build_brand_dna_brief_title(brand),
        content=build_brand_dna_brief_content(brand),
    )
    db.add(brief)
    db.flush()
    job = Job(
        organization_id=brand.organization_id,
        brand_id=brand.id,
        brief_id=brief.id,
        title=build_brand_dna_job_title(brand),
        status='queued',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("/{brand_id}", response_model=BrandRead)
def get_brand(
    brand_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BrandRead:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    get_organization_membership(brand.organization_id, memberships)
    return BrandRead.model_validate(brand, from_attributes=True)


@router.patch("/{brand_id}", response_model=BrandRead)
def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> BrandRead:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    require_organization_manager(brand.organization_id, memberships)
    organization = db.get(Organization, brand.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(brand, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Brand slug already exists in organization") from exc
    db.refresh(brand)
    return BrandRead.model_validate(brand, from_attributes=True)


@router.delete("/{brand_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(
    brand_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> None:
    brand = db.get(Brand, brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    require_organization_manager(brand.organization_id, memberships)
    organization = db.get(Organization, brand.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    ensure_brand_hard_delete_allowed(db, brand)
    db.delete(brand)
    db.commit()
    return None
