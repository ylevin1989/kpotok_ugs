from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.product import Product

CONTENT_GENERATION_BRIEF_KIND = 'content_item_generation'
CONTENT_GENERATION_JOB_PREFIX = 'Generate content item: '
CONTENT_GENERATION_BRIEF_PREFIX = 'Content generation request: '


def _not_found(entity_name: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'{entity_name} not found')


def _scope_conflict(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)


def _serialize_product(product: Product) -> dict[str, Any]:
    return {
        'id': str(product.id),
        'name': product.name,
        'category': product.category,
        'description': product.description,
        'features': product.features,
        'benefits': product.benefits,
        'proofs': product.proofs,
        'objections': product.objections,
        'restrictions': product.restrictions,
        'dna_json': product.dna_json,
    }


def _serialize_audience_segment(audience_segment: AudienceSegment) -> dict[str, Any]:
    return {
        'id': str(audience_segment.id),
        'name': audience_segment.name,
        'description': audience_segment.description,
        'pain_points': audience_segment.pain_points,
        'goals': audience_segment.goals,
        'objections': audience_segment.objections,
        'keywords': audience_segment.keywords,
    }


def build_content_generation_request(db: Session, content_item: ContentItem, content_plan: ContentPlan) -> dict[str, Any]:
    if content_plan.organization_id != content_item.organization_id or content_plan.brand_id != content_item.brand_id:
        raise _scope_conflict('Content plan does not belong to organization and brand')

    brand = db.get(Brand, content_item.brand_id)
    if brand is None:
        raise _not_found('Brand')
    if brand.organization_id != content_item.organization_id:
        raise _scope_conflict('Brand does not belong to organization')

    product_context: dict[str, Any] | None = None
    if content_item.product_id is not None:
        product = db.get(Product, content_item.product_id)
        if product is None:
            raise _not_found('Product')
        if product.organization_id != content_item.organization_id or product.brand_id != content_item.brand_id:
            raise _scope_conflict('Product does not belong to organization and brand')
        if content_item.scope == 'product' and content_plan.scope == 'product' and content_plan.product_id != content_item.product_id:
            raise _scope_conflict('Content plan product does not match content item product scope')
        product_context = _serialize_product(product)

    audience_context: dict[str, Any] | None = None
    if content_item.audience_segment_id is not None:
        audience_segment = db.get(AudienceSegment, content_item.audience_segment_id)
        if audience_segment is None:
            raise _not_found('Audience segment')
        if audience_segment.organization_id != content_item.organization_id or audience_segment.brand_id != content_item.brand_id:
            raise _scope_conflict('Audience segment does not belong to organization and brand')
        if content_item.scope == 'product' and audience_segment.product_id is not None and audience_segment.product_id != content_item.product_id:
            raise _scope_conflict('Audience segment product does not match content item product scope')
        audience_context = _serialize_audience_segment(audience_segment)

    if content_item.scope == 'product' and content_item.product_id is None:
        raise _scope_conflict('Product-scoped content item requires a product')

    if content_item.scope == 'product' and content_plan.product_id is not None and content_plan.product_id != content_item.product_id:
        raise _scope_conflict('Content plan product does not match content item product scope')

    return {
        'kind': CONTENT_GENERATION_BRIEF_KIND,
        'organization_id': str(content_item.organization_id),
        'brand_id': str(content_item.brand_id),
        'content_item_id': str(content_item.id),
        'content_plan_id': str(content_plan.id),
        'brand_context': {
            'id': str(brand.id),
            'name': brand.name,
            'dna_json': brand.dna_json,
        },
        'product_context': product_context,
        'audience_context': audience_context,
        'channel': {
            'goal': content_plan.goal,
            'platform': content_plan.platform,
            'date': content_plan.date.isoformat(),
        },
        'task': {
            'platform': content_item.platform,
            'content_type': content_item.content_type,
            'goal': content_item.goal,
            'title': content_item.title,
            'scope': content_item.scope,
        },
    }


def build_content_generation_brief_content(db: Session, content_item: ContentItem, content_plan: ContentPlan) -> str:
    return json.dumps(build_content_generation_request(db, content_item, content_plan))


def build_content_generation_job_title(content_item: ContentItem) -> str:
    return f'{CONTENT_GENERATION_JOB_PREFIX}{content_item.title}'


def build_content_generation_brief_title(content_item: ContentItem) -> str:
    return f'{CONTENT_GENERATION_BRIEF_PREFIX}{content_item.title}'


def parse_content_generation_request(brief: Brief | None) -> dict[str, Any] | None:
    if brief is None or not brief.content:
        return None
    try:
        payload = json.loads(brief.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get('kind') != CONTENT_GENERATION_BRIEF_KIND:
        return None
    return payload


def parse_content_generation_output(output_text: str | None) -> tuple[dict[str, Any] | None, str | None]:
    if output_text is None:
        return None, None
    try:
        payload = json.loads(output_text)
    except json.JSONDecodeError:
        return None, output_text.strip() or None
    if not isinstance(payload, dict):
        return None, output_text.strip() or None
    body_markdown = payload.get('body_markdown')
    if not isinstance(body_markdown, str) or not body_markdown.strip():
        return None, output_text.strip() or None
    required_fields = ('title', 'text', 'short_text', 'cta', 'visual_task', 'image_prompt', 'risks')
    structured_json = {field: payload.get(field) for field in required_fields}
    if any(structured_json[field] is None for field in required_fields):
        return None, output_text.strip() or None
    return structured_json, body_markdown.strip()


def parse_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None
