# Tickets

## Purpose
Tickets are the review/workflow records created around content item approvals.

## Core fields
- `organization_id`
- `brand_id`
- `product_id` (optional)
- `content_item_id`
- `content_version_id` (optional)
- `type`
- `reason_codes`
- `comment`
- `status`
- `priority`
- `assigned_agent_role`
- `created_by_id`
- `resolved_at`

## API surface
- `GET /api/v1/tickets?organization_id=...&content_item_id=...`
- `GET /api/v1/tickets/{ticket_id}`
- `POST /api/v1/tickets`
- `POST /api/v1/content-items/{content_item_id}/approve`
- `POST /api/v1/content-items/{content_item_id}/reject`
- `POST /api/v1/content-items/{content_item_id}/request-revision`

## Workflow
- `approve` marks the content item as `approved` and creates a resolved approval ticket.
- `reject` marks the content item as `rejected` and creates an open rejection ticket.
- `request-revision` marks the content item as `revision_requested` and creates an open revision ticket.
- `POST /api/v1/tickets/{ticket_id}/process` creates a queued revision job for an open ticket, and job completion writes the result back as a new content version plus a new quality check that gates the item toward client review or `internal_review`.
- Review actions require manager access on the owning organization.
- Review tickets link to the current content version when one exists.

## Verification
- `tests/test_packet167.py`
- full API regression remains green after the packet
