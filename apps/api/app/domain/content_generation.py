from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan

CONTENT_GENERATION_BRIEF_KIND = 'content_item_generation'
CONTENT_GENERATION_JOB_PREFIX = 'Generate content item: '
CONTENT_GENERATION_BRIEF_PREFIX = 'Content generation request: '


def build_content_generation_request(content_item: ContentItem, content_plan: ContentPlan) -> dict[str, Any]:
    return {
        'kind': CONTENT_GENERATION_BRIEF_KIND,
        'content_item_id': str(content_item.id),
        'content_plan_id': str(content_plan.id),
        'organization_id': str(content_item.organization_id),
        'brand_id': str(content_item.brand_id),
        'product_id': str(content_item.product_id) if content_item.product_id is not None else None,
        'audience_segment_id': str(content_item.audience_segment_id) if content_item.audience_segment_id is not None else None,
        'scope': content_item.scope,
        'platform': content_item.platform,
        'content_type': content_item.content_type,
        'goal': content_item.goal,
        'title': content_item.title,
    }


def build_content_generation_brief_content(content_item: ContentItem, content_plan: ContentPlan) -> str:
    return json.dumps(build_content_generation_request(content_item, content_plan))


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


def parse_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None
