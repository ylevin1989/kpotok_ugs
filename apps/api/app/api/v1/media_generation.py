from __future__ import annotations

import os
import uuid
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.core.config import settings
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_version import ContentVersion
from app.db.models.media_asset import MediaAsset
from app.db.models.organization import OrganizationMembership
from app.db.models.product import Product
from app.db.session import get_db
from app.domain.image_prompt import build_image_prompt
from app.domain.kie_client import download_bytes, generate_image_url
from app.storage import get_storage_client

router = APIRouter(tags=['media-generation'])

_MAX_REFERENCES_FOR_GENERATION = 4


def _api_base() -> str:
    return os.environ.get('CF_API_URL', 'https://apiha.uno-ai.pw').rstrip('/')


def _ext_for(content_type: str) -> str:
    if 'png' in content_type:
        return 'png'
    if 'jpeg' in content_type or 'jpg' in content_type:
        return 'jpg'
    if 'webp' in content_type:
        return 'webp'
    return 'img'


def _put_object(key: str, data: bytes, content_type: str) -> None:
    client = get_storage_client(settings)
    if not client.bucket_exists(settings.s3_bucket):
        client.make_bucket(settings.s3_bucket)
    client.put_object(settings.s3_bucket, key, BytesIO(data), length=len(data), content_type=content_type)


def _get_object(key: str) -> bytes:
    client = get_storage_client(settings)
    resp = client.get_object(settings.s3_bucket, key)
    try:
        return resp.read()
    finally:
        resp.close()
        resp.release_conn()


def _post_text(db: Session, item: ContentItem) -> str:
    if item.current_version_id:
        version = db.get(ContentVersion, item.current_version_id)
        if version and version.body_markdown:
            return version.body_markdown
    return item.title or ''


def _product_reference_public_urls(db: Session, item: ContentItem) -> list[str]:
    if not item.product_id:
        return []
    frag = f'/products/{item.product_id}/references/'
    refs = (
        db.query(MediaAsset)
        .filter(MediaAsset.organization_id == item.organization_id, MediaAsset.asset_key.like(f'%{frag}%'))
        .order_by(MediaAsset.created_at.desc())
        .limit(_MAX_REFERENCES_FOR_GENERATION)
        .all()
    )
    base = _api_base()
    return [f'{base}/api/v1/media-assets/{r.id}/public' for r in refs]


@router.post('/content-items/{item_id}/generate-image', status_code=status.HTTP_201_CREATED)
def generate_content_item_image(
    item_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(ContentItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    require_organization_manager(item.organization_id, memberships)
    brand = db.get(Brand, item.brand_id)
    if brand is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Brand not found')
    product = db.get(Product, item.product_id) if item.product_id else None

    post_text = _post_text(db, item)
    reference_urls = _product_reference_public_urls(db, item)
    try:
        image_prompt = build_image_prompt(post_text=post_text, brand=brand, product=product)
        image_url = generate_image_url(image_prompt, image_urls=reference_urls or None)
        image_bytes, content_type = download_bytes(image_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Image generation failed: {exc}')

    asset_key = f'organizations/{item.organization_id}/brands/{item.brand_id}/content-items/{item.id}/images/{uuid.uuid4()}.{_ext_for(content_type)}'
    try:
        _put_object(asset_key, image_bytes, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Storage upload failed: {exc}')

    asset = MediaAsset(
        organization_id=item.organization_id,
        brand_id=item.brand_id,
        product_id=item.product_id,
        scope=item.scope,
        name=f'Изображение: {item.title[:180]}',
        description=image_prompt[:2000],
        asset_key=asset_key,
        source_url=image_url,
        content_type=content_type,
        size_bytes=len(image_bytes),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {
        'id': str(asset.id),
        'content_item_id': str(item.id),
        'image_prompt': image_prompt,
        'content_type': content_type,
        'size_bytes': len(image_bytes),
        'used_references': len(reference_urls),
        'file_url': f'/api/v1/media-assets/{asset.id}/file',
    }


@router.get('/content-items/{item_id}/images')
def list_content_item_images(
    item_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> dict:
    item = db.get(ContentItem, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content item not found')
    get_organization_membership(item.organization_id, memberships)
    frag = f'/content-items/{item.id}/images/'
    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.organization_id == item.organization_id, MediaAsset.asset_key.like(f'%{frag}%'))
        .order_by(MediaAsset.created_at.desc())
        .all()
    )
    return {
        'items': [
            {
                'id': str(a.id),
                'image_prompt': a.description,
                'content_type': a.content_type,
                'file_url': f'/api/v1/media-assets/{a.id}/file',
                'created_at': a.created_at.isoformat() if a.created_at else None,
            }
            for a in assets
        ]
    }


# ---------- References ----------
@router.post('/references', status_code=status.HTTP_201_CREATED)
async def upload_reference(
    organization_id: UUID = Form(...),
    brand_id: UUID = Form(...),
    product_id: UUID | None = Form(default=None),
    file: UploadFile = File(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> dict:
    require_organization_manager(organization_id, memberships)
    brand = db.get(Brand, brand_id)
    if brand is None or brand.organization_id != organization_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Brand not found in organization')
    if product_id is not None:
        product = db.get(Product, product_id)
        if product is None or product.organization_id != organization_id or product.brand_id != brand_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Product not found in brand')
    data = await file.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Empty file')
    content_type = file.content_type or 'image/png'
    if not content_type.startswith('image/'):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Only image files are allowed')
    if product_id is not None:
        key = f'organizations/{organization_id}/products/{product_id}/references/{uuid.uuid4()}.{_ext_for(content_type)}'
        scope = 'product'
    else:
        key = f'organizations/{organization_id}/brands/{brand_id}/references/{uuid.uuid4()}.{_ext_for(content_type)}'
        scope = 'brand'
    try:
        _put_object(key, data, content_type)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Storage upload failed: {exc}')
    asset = MediaAsset(
        organization_id=organization_id,
        brand_id=brand_id,
        product_id=product_id,
        scope=scope,
        name=(file.filename or 'reference')[:200],
        description='reference',
        asset_key=key,
        source_url=None,
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return {'id': str(asset.id), 'name': asset.name, 'file_url': f'/api/v1/media-assets/{asset.id}/file'}


@router.get('/references')
def list_references(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    product_id: UUID | None = Query(default=None),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> dict:
    get_organization_membership(organization_id, memberships)
    frag = f'/products/{product_id}/references/' if product_id is not None else f'/brands/{brand_id}/references/'
    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.organization_id == organization_id, MediaAsset.asset_key.like(f'%{frag}%'))
        .order_by(MediaAsset.created_at.desc())
        .all()
    )
    return {
        'items': [
            {'id': str(a.id), 'name': a.name, 'content_type': a.content_type, 'file_url': f'/api/v1/media-assets/{a.id}/file', 'created_at': a.created_at.isoformat() if a.created_at else None}
            for a in assets
        ]
    }


@router.delete('/references/{media_id}', status_code=status.HTTP_204_NO_CONTENT)
def delete_reference(
    media_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> Response:
    asset = db.get(MediaAsset, media_id)
    if asset is None or '/references/' not in asset.asset_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Reference not found')
    require_organization_manager(asset.organization_id, memberships)
    db.delete(asset)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Serving ----------
@router.get('/media-assets/{media_id}/file')
def get_media_asset_file(
    media_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> Response:
    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Media asset not found')
    get_organization_membership(asset.organization_id, memberships)
    try:
        payload = _get_object(asset.asset_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'File not available: {exc}')
    return Response(content=payload, media_type=asset.content_type or 'application/octet-stream')


@router.get('/media-assets/{media_id}/public')
def get_media_asset_public(media_id: UUID, db: Session = Depends(get_db)) -> Response:
    """Unauthenticated read by opaque UUID — used so kie.ai can fetch reference images."""
    asset = db.get(MediaAsset, media_id)
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Media asset not found')
    try:
        payload = _get_object(asset.asset_key)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'File not available: {exc}')
    return Response(content=payload, media_type=asset.content_type or 'application/octet-stream')
