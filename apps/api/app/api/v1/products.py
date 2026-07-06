from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.jobs import _job_read
from app.api.v1.organizations import ensure_content_organization_writable
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.product import Product
from app.db.session import get_db
from app.domain.dna_generation import (
    build_product_dna_brief_content,
    build_product_dna_brief_title,
    build_product_dna_job_title,
)
from app.schemas.product import ProductCreate, ProductListResponse, ProductRead, ProductUpdate
from app.schemas.job import JobRead

router = APIRouter(prefix="/products", tags=["products"])


def get_product_in_organization_brand(db: Session, product_id: UUID, organization_id: UUID, brand_id: UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    if product.organization_id != organization_id or product.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product does not belong to organization and brand")
    return product


@router.get("", response_model=ProductListResponse)
def list_products(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ProductListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    items = db.execute(
        select(Product)
        .where(Product.organization_id == organization_id, Product.brand_id == brand_id)
        .order_by(Product.created_at.asc())
    ).scalars().all()
    return ProductListResponse(items=[ProductRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ProductRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    product = Product(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        sku=payload.sku,
        name=payload.name,
        category=payload.category,
        description=payload.description,
        features=payload.features,
        benefits=payload.benefits,
        proofs=payload.proofs,
        objections=payload.objections,
        restrictions=payload.restrictions,
        status=payload.status,
        readiness_score=payload.readiness_score,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists in organization and brand") from exc
    db.refresh(product)
    return ProductRead.model_validate(product, from_attributes=True)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_organization_manager(product.organization_id, memberships)
    organization = db.get(Organization, product.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(product, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Product SKU already exists in organization and brand") from exc
    db.refresh(product)
    return ProductRead.model_validate(product, from_attributes=True)


@router.post("/{product_id}/generate-dna", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def generate_product_dna(
    product_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> JobRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    require_organization_manager(product.organization_id, memberships)
    organization = db.get(Organization, product.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, product.brand_id, product.organization_id)
    brief = Brief(
        organization_id=product.organization_id,
        brand_id=product.brand_id,
        title=build_product_dna_brief_title(product),
        content=build_product_dna_brief_content(product),
    )
    db.add(brief)
    db.flush()
    job = Job(
        organization_id=product.organization_id,
        brand_id=product.brand_id,
        brief_id=brief.id,
        title=build_product_dna_job_title(product),
        status='queued',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return _job_read(job)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ProductRead:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    get_organization_membership(product.organization_id, memberships)
    return ProductRead.model_validate(product, from_attributes=True)
