from __future__ import annotations

from datetime import date as _date

import csv
import io
import json
from datetime import date as DateType, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_accessible_memberships, get_organization_membership, require_organization_manager
from app.api.v1.audience_segments import get_audience_segment_in_organization_brand
from app.api.v1.brand_lifecycle import ensure_brand_content_writable
from app.api.v1.briefs import get_brand_in_organization
from app.api.v1.organizations import ensure_content_organization_writable
from app.api.v1.products import get_product_in_organization_brand
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.content_plan import ContentPlan
from app.domain.content_plan_generation import generate_plan_items
from app.db.models.organization import Organization, OrganizationMembership
from app.db.models.product import Product
from app.db.session import get_db
from app.domain.billing import (
    CONTENT_PLAN_EXPORT_METRIC,
    CONTENT_PLAN_GENERATION_METRIC,
    enforce_usage_limit,
    get_or_create_subscription,
    record_usage,
)
from app.domain.content_scope import ContentScope
from app.schemas.content_plan import ContentPlanCreate, ContentPlanExport, ContentPlanGenerate, ContentPlanListResponse, ContentPlanRead

router = APIRouter(prefix="/content-plans", tags=["content-plans"])


def get_content_plan_in_organization_brand(db: Session, content_plan_id: UUID, organization_id: UUID, brand_id: UUID) -> ContentPlan:
    content_plan = db.get(ContentPlan, content_plan_id)
    if content_plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Content plan not found")
    if content_plan.organization_id != organization_id or content_plan.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Content plan does not belong to organization and brand")
    return content_plan


def _extract_context_terms(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        stripped = value.strip()
        return [stripped] if stripped else []
    if isinstance(value, dict):
        terms: list[str] = []
        for item in value.values():
            terms.extend(_extract_context_terms(item))
        return terms
    if isinstance(value, (list, tuple, set)):
        terms: list[str] = []
        for item in value:
            terms.extend(_extract_context_terms(item))
        return terms
    text = str(value).strip()
    return [text] if text else []


def _build_generation_context(brand: Brand, product: Product | None, audience_segment: AudienceSegment | None) -> str:
    parts: list[str] = [brand.name]
    if product is not None:
        parts.append(product.name)
    if audience_segment is not None:
        parts.append(audience_segment.name)
    parts.extend(_extract_context_terms(brand.dna_json))
    if product is not None:
        parts.extend(_extract_context_terms(product.dna_json))
    if audience_segment is not None:
        parts.extend(audience_segment.pain_points)
        parts.extend(audience_segment.goals)
        parts.extend(audience_segment.keywords)
    unique_parts: list[str] = []
    for part in parts:
        normalized = part.strip()
        if normalized and normalized not in unique_parts:
            unique_parts.append(normalized)
    return ' · '.join(unique_parts[:5])


def _serialize_content_plan(item: ContentPlan) -> dict[str, object]:
    return {
        'id': str(item.id),
        'organization_id': str(item.organization_id),
        'brand_id': str(item.brand_id),
        'product_id': str(item.product_id) if item.product_id is not None else None,
        'audience_segment_id': str(item.audience_segment_id) if item.audience_segment_id is not None else None,
        'scope': item.scope,
        'date': item.date.isoformat(),
        'title': item.title,
        'platform': item.platform,
        'content_type': item.content_type,
        'goal': item.goal,
        'status': item.status,
        'created_at': item.created_at.isoformat(),
        'updated_at': item.updated_at.isoformat(),
    }


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
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)
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


@router.post("/generate", response_model=ContentPlanListResponse, status_code=status.HTTP_201_CREATED)
def generate_content_plans(
    payload: ContentPlanGenerate,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> ContentPlanListResponse:
    require_organization_manager(payload.organization_id, memberships)
    organization = db.get(Organization, payload.organization_id)
    if organization is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    ensure_content_organization_writable(organization)
    subscription = get_or_create_subscription(db, payload.organization_id)
    if not subscription.is_active:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail='Subscription is inactive')
    quantity = (payload.end_date - payload.start_date).days + 1
    enforce_usage_limit(
        db,
        organization_id=payload.organization_id,
        metric=CONTENT_PLAN_GENERATION_METRIC,
        quantity=quantity,
        limit=subscription.monthly_content_plan_limit,
        error_detail='Monthly content-plan limit exceeded',
    )
    brand = get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    ensure_brand_content_writable(brand)
    product: Product | None = None
    if payload.product_id is not None:
        product = get_product_in_organization_brand(db, payload.product_id, payload.organization_id, payload.brand_id)
    audience_segment: AudienceSegment | None = None
    if payload.audience_segment_id is not None:
        audience_segment = get_audience_segment_in_organization_brand(db, payload.audience_segment_id, payload.organization_id, payload.brand_id)

    try:
        generated = generate_plan_items(
            brand=brand, product=product, audience=audience_segment,
            platform=payload.platform, start=payload.start_date, end=payload.end_date, goal=payload.goal,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f'Content plan generation failed: {exc}')

    items: list[ContentPlan] = []
    for g in generated:
        try:
            item_date = _date.fromisoformat(g['date'])
        except ValueError:
            item_date = payload.start_date
        if item_date < payload.start_date or item_date > payload.end_date:
            item_date = payload.start_date
        goal_text = g['brief'] or payload.goal
        if g.get('funnel_stage'):
            goal_text = f"[{g['funnel_stage']}] {goal_text}"
        content_plan = ContentPlan(
            organization_id=payload.organization_id,
            brand_id=payload.brand_id,
            product_id=payload.product_id,
            audience_segment_id=payload.audience_segment_id,
            scope=payload.scope.value,
            date=item_date,
            title=g['title'],
            platform=payload.platform,
            content_type=g['content_type'] or payload.content_type,
            goal=goal_text,
            status=payload.status,
        )
        db.add(content_plan)
        items.append(content_plan)
    db.commit()
    for item in items:
        db.refresh(item)
    record_usage(
        db,
        organization_id=payload.organization_id,
        subscription=subscription,
        metric=CONTENT_PLAN_GENERATION_METRIC,
        quantity=quantity,
        metadata={'brand_id': str(payload.brand_id), 'scope': payload.scope.value},
    )
    return ContentPlanListResponse(items=[ContentPlanRead.model_validate(item, from_attributes=True) for item in items])


@router.post("/export")
def export_content_plans(
    payload: ContentPlanExport,
    memberships: list[OrganizationMembership] = Depends(get_accessible_memberships),
    db: Session = Depends(get_db),
) -> Response:
    get_organization_membership(payload.organization_id, memberships)
    get_brand_in_organization(db, payload.brand_id, payload.organization_id)
    subscription = get_or_create_subscription(db, payload.organization_id)
    if not subscription.is_active:
        raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail='Subscription is inactive')
    query = select(ContentPlan).where(ContentPlan.organization_id == payload.organization_id, ContentPlan.brand_id == payload.brand_id)
    if payload.scope is not None:
        query = query.where(ContentPlan.scope == payload.scope.value)
    if payload.product_id is not None:
        query = query.where(ContentPlan.product_id == payload.product_id)
    if payload.audience_segment_id is not None:
        query = query.where(ContentPlan.audience_segment_id == payload.audience_segment_id)
    items = db.execute(query.order_by(ContentPlan.date.asc(), ContentPlan.created_at.asc())).scalars().all()
    enforce_usage_limit(
        db,
        organization_id=payload.organization_id,
        metric=CONTENT_PLAN_EXPORT_METRIC,
        quantity=1,
        limit=subscription.monthly_export_limit,
        error_detail='Monthly export limit exceeded',
    )
    serialized_items = [_serialize_content_plan(item) for item in items]
    record_usage(
        db,
        organization_id=payload.organization_id,
        subscription=subscription,
        metric=CONTENT_PLAN_EXPORT_METRIC,
        quantity=1,
        metadata={'brand_id': str(payload.brand_id), 'format': payload.format, 'item_count': len(serialized_items)},
    )
    filename = f"content-plans-{payload.organization_id}-{payload.brand_id}.{payload.format}"
    if payload.format == 'json':
        return Response(
            content=json.dumps({'items': serialized_items}, ensure_ascii=False),
            media_type='application/json',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )

    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(serialized_items[0].keys()) if serialized_items else [
        'id', 'organization_id', 'brand_id', 'product_id', 'audience_segment_id', 'scope', 'date', 'title', 'platform', 'content_type', 'goal', 'status', 'created_at', 'updated_at'
    ])
    writer.writeheader()
    for row in serialized_items:
        writer.writerow(row)
    return Response(
        content=buffer.getvalue(),
        media_type='text/csv',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


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
