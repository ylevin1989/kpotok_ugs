from __future__ import annotations

import csv
import io
import json
import zipfile
from collections.abc import Iterator
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage as storage_module
from app.api.deps import get_accessible_memberships, get_current_user, get_organization_membership, require_organization_manager
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.content_plans import get_content_plan_in_organization_brand
from app.api.v1.organizations import ensure_content_organization_writable
from app.core.config import settings
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.export import Export
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.user import User
from app.db.session import get_db
from app.db.enums import ExportFormat, ExportStatus
from app.domain.billing import CONTENT_PLAN_EXPORT_METRIC, enforce_usage_limit, get_or_create_subscription, record_usage
from app.schemas.export import ContentPlanExportCreate, ExportCreate, ExportListResponse, ExportRead

router = APIRouter(tags=['exports'])


CONTENT_ITEM_CSV_FIELDS = [
    'content_item_id',
    'content_plan_id',
    'title',
    'status',
    'platform',
    'content_type',
    'goal',
    'body_markdown',
    'structured_json',
]


def _serialize_export(export: Export) -> ExportRead:
    return ExportRead.model_validate(export, from_attributes=True)


def _expected_export_prefix(export: Export) -> str:
    return f'organizations/{export.organization_id}/brands/{export.brand_id}/exports/{export.id}/'


def _expected_export_key(export: Export) -> str:
    suffix = {
        ExportFormat.MARKDOWN: 'content-items.md',
        ExportFormat.CSV: 'content-items.csv',
        ExportFormat.ZIP: 'content-items.zip',
    }[export.format]
    return f'{_expected_export_prefix(export)}{suffix}'


def _load_export_in_scope(db: Session, export_id: UUID, memberships: list[OrganizationMembership]) -> Export:
    export = db.get(Export, export_id)
    if export is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Export not found')
    get_organization_membership(export.organization_id, memberships)
    return export


def _normalize_filters(payload: ExportCreate) -> dict[str, str]:
    filters: dict[str, str] = {}
    if payload.content_plan_id is not None:
        filters['content_plan_id'] = str(payload.content_plan_id)
    if payload.scope is not None:
        filters['scope'] = payload.scope.value
    if payload.product_id is not None:
        filters['product_id'] = str(payload.product_id)
    if payload.audience_segment_id is not None:
        filters['audience_segment_id'] = str(payload.audience_segment_id)
    return filters


def _approved_rows(db: Session, export: Export) -> list[dict[str, str]]:
    query = (
        select(ContentItem, ContentVersion)
        .join(ContentVersion, ContentVersion.id == ContentItem.current_version_id)
        .where(
            ContentItem.organization_id == export.organization_id,
            ContentItem.brand_id == export.brand_id,
            ContentItem.status == 'approved',
        )
        .order_by(ContentItem.created_at.asc())
    )

    filters = export.filter_json or {}
    if export.content_plan_id is not None:
        query = query.where(ContentItem.content_plan_id == export.content_plan_id)
    if filters.get('scope'):
        query = query.where(ContentItem.scope == filters['scope'])
    if filters.get('product_id'):
        query = query.where(ContentItem.product_id == UUID(filters['product_id']))
    if filters.get('audience_segment_id'):
        query = query.where(ContentItem.audience_segment_id == UUID(filters['audience_segment_id']))

    results = db.execute(query).all()
    rows: list[dict[str, str]] = []
    for content_item, version in results:
        rows.append(
            {
                'content_item_id': str(content_item.id),
                'content_plan_id': str(content_item.content_plan_id),
                'title': content_item.title,
                'status': content_item.status,
                'platform': content_item.platform,
                'content_type': content_item.content_type,
                'goal': content_item.goal,
                'body_markdown': version.body_markdown or '',
                'structured_json': json.dumps(version.structured_json, ensure_ascii=False, sort_keys=True) if version.structured_json is not None else '',
            }
        )
    return rows


def _render_markdown(rows: list[dict[str, str]], export: Export) -> bytes:
    lines = [
        f'# Export {export.id}',
        '',
        f'- organization_id: {export.organization_id}',
        f'- brand_id: {export.brand_id}',
        f'- content_plan_id: {export.content_plan_id if export.content_plan_id is not None else "all"}',
        f'- approved_item_count: {len(rows)}',
        '',
    ]
    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f'## {index}. {row["title"]}',
                '',
                f'- content_item_id: {row["content_item_id"]}',
                f'- content_plan_id: {row["content_plan_id"]}',
                f'- platform: {row["platform"]}',
                f'- content_type: {row["content_type"]}',
                f'- goal: {row["goal"]}',
                '',
                row['body_markdown'] or '_No markdown body_',
                '',
            ]
        )
        if row['structured_json']:
            lines.extend(['```json', row['structured_json'], '```', ''])
    return '\n'.join(lines).encode('utf-8')


def _render_csv(rows: list[dict[str, str]]) -> bytes:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=CONTENT_ITEM_CSV_FIELDS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue().encode('utf-8')


def _render_zip(rows: list[dict[str, str]], export: Export) -> bytes:
    markdown_payload = _render_markdown(rows, export)
    csv_payload = _render_csv(rows)
    manifest = {
        'export_id': str(export.id),
        'organization_id': str(export.organization_id),
        'brand_id': str(export.brand_id),
        'content_plan_id': str(export.content_plan_id) if export.content_plan_id is not None else None,
        'approved_item_count': len(rows),
        'format': export.format.value,
        'filters': export.filter_json or {},
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('content-items.md', markdown_payload)
        archive.writestr('content-items.csv', csv_payload)
        archive.writestr('manifest.json', json.dumps(manifest, ensure_ascii=False, indent=2))
    return buffer.getvalue()


def _render_payload(export: Export, rows: list[dict[str, str]]) -> tuple[bytes, str]:
    if export.format == ExportFormat.MARKDOWN:
        return _render_markdown(rows, export), 'text/markdown; charset=utf-8'
    if export.format == ExportFormat.CSV:
        return _render_csv(rows), 'text/csv; charset=utf-8'
    if export.format == ExportFormat.ZIP:
        return _render_zip(rows, export), 'application/zip'
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported export format')


def _persist_export_file(export: Export, payload: bytes, content_type: str) -> None:
    file_key = _expected_export_key(export)
    client = storage_module.get_storage_client(settings)
    client.put_object(
        settings.s3_bucket,
        file_key,
        io.BytesIO(payload),
        length=len(payload),
        content_type=content_type,
    )
    export.file_key = file_key
    export.file_size_bytes = len(payload)
    export.content_type = content_type
    export.status = ExportStatus.READY
    export.error_message = None


def _stream_export_file(export: Export) -> StreamingResponse:
    if export.status != ExportStatus.READY or not export.file_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Export artifact is not ready')
    if not export.file_key.startswith(_expected_export_prefix(export)):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Export artifact key is outside the export tenant namespace')

    client = storage_module.get_storage_client(settings)
    response = client.get_object(settings.s3_bucket, export.file_key)

    def iterator() -> Iterator[bytes]:
        try:
            if hasattr(response, 'stream'):
                yield from response.stream(amt=64 * 1024)
            else:
                yield response.read()
        finally:
            if hasattr(response, 'close'):
                response.close()
            if hasattr(response, 'release_conn'):
                response.release_conn()

    filename = export.file_key.rsplit('/', 1)[-1]
    return StreamingResponse(
        iterator(),
        media_type=export.content_type or 'application/octet-stream',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


def create_and_store_export(
    *,
    db: Session,
    current_user: User,
    organization_id: UUID,
    brand_id: UUID,
    format: ExportFormat,
    content_plan_id: UUID | None = None,
    filters: dict[str, str] | None = None,
) -> Export:
    organization = db.get(Organization, organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Organization not found')
    ensure_content_organization_writable(organization)
    get_brand_in_organization(db, brand_id, organization_id)
    if content_plan_id is not None:
        get_content_plan_in_organization_brand(db, content_plan_id, organization_id, brand_id)

    subscription = get_or_create_subscription(db, organization_id)
    if not subscription.is_active:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail='Subscription is inactive')
    enforce_usage_limit(
        db,
        organization_id=organization_id,
        metric=CONTENT_PLAN_EXPORT_METRIC,
        quantity=1,
        limit=subscription.monthly_export_limit,
        error_detail='Monthly export limit exceeded',
    )

    export = Export(
        organization_id=organization_id,
        brand_id=brand_id,
        content_plan_id=content_plan_id,
        format=format,
        status=ExportStatus.PENDING,
        filter_json=filters or None,
        created_by=current_user.id,
    )
    db.add(export)
    db.flush()

    try:
        rows = _approved_rows(db, export)
        payload, content_type = _render_payload(export, rows)
        _persist_export_file(export, payload, content_type)
    except Exception as exc:
        export.status = ExportStatus.FAILED
        export.error_message = str(exc)
        db.commit()
        raise

    db.commit()
    db.refresh(export)
    record_usage(
        db,
        organization_id=organization_id,
        subscription=subscription,
        metric=CONTENT_PLAN_EXPORT_METRIC,
        quantity=1,
        metadata={
            'brand_id': str(brand_id),
            'content_plan_id': str(content_plan_id) if content_plan_id is not None else None,
            'format': format.value,
            'approved_item_count': len(rows),
        },
    )
    return export


@router.post('/content-plans/{content_plan_id}/export', response_model=ExportRead, status_code=status.HTTP_201_CREATED)
def export_content_plan(
    content_plan_id: UUID,
    payload: ContentPlanExportCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportRead:
    content_plan = db.get(ContentPlan, content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Content plan not found')
    require_organization_manager(content_plan.organization_id, memberships)
    export = create_and_store_export(
        db=db,
        current_user=current_user,
        organization_id=content_plan.organization_id,
        brand_id=content_plan.brand_id,
        format=payload.format,
        content_plan_id=content_plan.id,
        filters=None,
    )
    return _serialize_export(export)


@router.post('/exports', response_model=ExportRead, status_code=status.HTTP_201_CREATED)
def create_export(
    payload: ExportCreate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExportRead:
    require_organization_manager(payload.organization_id, memberships)
    export = create_and_store_export(
        db=db,
        current_user=current_user,
        organization_id=payload.organization_id,
        brand_id=payload.brand_id,
        format=payload.format,
        content_plan_id=payload.content_plan_id,
        filters=_normalize_filters(payload),
    )
    return _serialize_export(export)


@router.get('/exports', response_model=ExportListResponse)
def list_exports(
    organization_id: UUID = Query(...),
    brand_id: UUID = Query(...),
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ExportListResponse:
    get_organization_membership(organization_id, memberships)
    get_brand_in_organization(db, brand_id, organization_id)
    items = db.execute(
        select(Export)
        .where(Export.organization_id == organization_id, Export.brand_id == brand_id)
        .order_by(Export.created_at.desc())
    ).scalars().all()
    return ExportListResponse(items=[_serialize_export(item) for item in items])


@router.get('/exports/{export_id}', response_model=ExportRead)
def get_export(
    export_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ExportRead:
    export = _load_export_in_scope(db, export_id, memberships)
    return _serialize_export(export)


@router.get('/exports/{export_id}/download')
def download_export(
    export_id: UUID,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    export = _load_export_in_scope(db, export_id, memberships)
    return _stream_export_file(export)
