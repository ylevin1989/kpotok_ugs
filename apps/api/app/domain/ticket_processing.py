from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.db.models.brief import Brief
from app.db.models.content_item import ContentItem
from app.db.models.ticket import Ticket

TICKET_PROCESSING_BRIEF_KIND = 'content_item_ticket_revision'
TICKET_PROCESSING_JOB_PREFIX = 'Process ticket: '
TICKET_PROCESSING_BRIEF_PREFIX = 'Ticket processing request: '


def build_ticket_processing_request(ticket: Ticket, content_item: ContentItem) -> dict[str, Any]:
    return {
        'kind': TICKET_PROCESSING_BRIEF_KIND,
        'ticket_id': str(ticket.id),
        'content_item_id': str(content_item.id),
        'content_version_id': str(ticket.content_version_id) if ticket.content_version_id is not None else None,
        'organization_id': str(ticket.organization_id),
        'brand_id': str(ticket.brand_id),
        'product_id': str(ticket.product_id) if ticket.product_id is not None else None,
        'type': ticket.type,
        'reason_codes': list(ticket.reason_codes or []),
        'comment': ticket.comment,
        'assigned_agent_role': ticket.assigned_agent_role,
        'title': content_item.title,
    }


def build_ticket_processing_brief_content(ticket: Ticket, content_item: ContentItem) -> str:
    return json.dumps(build_ticket_processing_request(ticket, content_item))


def build_ticket_processing_job_title(ticket: Ticket, content_item: ContentItem) -> str:
    return f'{TICKET_PROCESSING_JOB_PREFIX}{content_item.title}'


def build_ticket_processing_brief_title(ticket: Ticket, content_item: ContentItem) -> str:
    return f'{TICKET_PROCESSING_BRIEF_PREFIX}{content_item.title}'


def parse_ticket_processing_request(brief: Brief | None) -> dict[str, Any] | None:
    if brief is None or not brief.content:
        return None
    try:
        payload = json.loads(brief.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get('kind') != TICKET_PROCESSING_BRIEF_KIND:
        return None
    return payload


def parse_ticket_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None
