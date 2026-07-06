from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.models.media_asset import MediaAsset
from app.db.models.organization import Organization, OrganizationMembership
from app.db.session import get_db
from app.domain.content_scope import ContentScope
from app.schemas.media_asset import MediaAssetCreate, MediaAssetListResponse, MediaAssetRead

router = APIRouter(prefix="/media-assets", tags=["media-assets"])


def get_media_asset_in_organization_brand(db: Session, media_asset_id: UUID, organization_id: UUID, brand_id: UUID) -> MediaAsset:
    media_asset = db.get(MediaAsset, media_asset_id)
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    if media_asset.organization_id != organization_id or media_asset.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Media asset does not belong to organization and brand")
    return media_asset


@router.get("", response_model=MediaAssetListResponse)
def list_media_assets(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    scope: ContentScope | None = Query(default=None),
    product_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> MediaAssetListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    query = select(MediaAsset).where(MediaAsset.organization_id == organization_id, MediaAsset.brand_id == brand_id)
    if scope is not None:
        query = query.where(MediaAsset.scope == scope.value)
    if product_id is not None:
        query = query.where(MediaAsset.product_id == product_id)
    items = db.execute(query.order_by(MediaAsset.created_at.asc())).scalars().all()
    return MediaAssetListResponse(items=[MediaAssetRead.model_validate(item, from_attributes=True) for item in items])


@router.post("", response_model=MediaAssetRead, status_code=status.HTTP_201_CREATED)
def create_media_asset(
    payload: MediaAssetCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> MediaAssetRead:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    if payload.product_id is not None:
        get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    media_asset = MediaAsset(
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        product_id=payload.product_id,
        scope=payload.scope.value,
        name=payload.name,
        description=payload.description,
        asset_key=payload.asset_key,
        source_url=payload.source_url,
        content_type=payload.content_type,
        size_bytes=payload.size_bytes,
        checksum=payload.checksum,
    )
    db.add(media_asset)
    db.commit()
    db.refresh(media_asset)
    return MediaAssetRead.model_validate(media_asset, from_attributes=True)


@router.get("/{media_asset_id}", response_model=MediaAssetRead)
def get_media_asset(
    media_asset_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> MediaAssetRead:
    media_asset = db.get(MediaAsset, media_asset_id)
    if media_asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Media asset not found")
    get_organization_membership(media_asset.organization_id, memberships)
    return MediaAssetRead.model_validate(media_asset, from_attributes=True)
