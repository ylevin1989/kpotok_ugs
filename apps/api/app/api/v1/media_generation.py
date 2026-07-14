from __future__ import annotations

import uuid
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
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


def _post_text(db: Session, item: ContentItem) -> str:
    if item.current_version_id:
        version = db.get(ContentVersion, item.current_version_id)
        if version and version.body_markdown:
            return version.body_markdown
    return item.title or ''


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
    try:
        image_prompt = build_image_prompt(post_text=post_text, brand=brand, product=product)
        image_url = generate_image_url(image_prompt)
        image_bytes, content_type = download_bytes(image_url)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Image generation failed: {exc}')

    ext = 'png' if 'png' in content_type else ('jpg' if 'jpeg' in content_type or 'jpg' in content_type else 'img')
    asset_key = f'organizations/{item.organization_id}/brands/{item.brand_id}/content-items/{item.id}/images/{uuid.uuid4()}.{ext}'
    client = get_storage_client(settings)
    try:
        if not client.bucket_exists(settings.s3_bucket):
            client.make_bucket(settings.s3_bucket)
        client.put_object(settings.s3_bucket, asset_key, BytesIO(image_bytes), length=len(image_bytes), content_type=content_type)
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
    key_fragment = f'/content-items/{item.id}/images/'
    assets = (
        db.query(MediaAsset)
        .filter(MediaAsset.organization_id == item.organization_id, MediaAsset.asset_key.like(f'%{key_fragment}%'))
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
    client = get_storage_client(settings)
    try:
        resp = client.get_object(settings.s3_bucket, asset.asset_key)
        try:
            payload = resp.read()
        finally:
            resp.close()
            resp.release_conn()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'File not available: {exc}')
    return Response(content=payload, media_type=asset.content_type or 'application/octet-stream')
