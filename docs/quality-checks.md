# Quality Checks

## Purpose
Quality checks capture QA results for a specific content item and content version.

## Core fields
- `organization_id`
- `brand_id`
- `product_id` (optional)
- `content_item_id`
- `content_version_id`
- `ticket_id` (optional)
- `score`
- `threshold`
- `status`
- `summary`
- `checks_json`
- `issues_json`
- `recommendations_json`
- `generated_from_task_id` (optional)
- `created_by_id`
- `checked_at`

## API surface
- `GET /api/v1/quality-checks?organization_id=...`
- `GET /api/v1/quality-checks/{quality_check_id}`
- `POST /api/v1/content-items/{content_item_id}/quality-check`

## Workflow
- The create endpoint resolves the target content version from the request, ticket, or current content item version.
- The quality check computes the score from the actual content/body plus brand and product context, then stores the structured QA findings.
- The latest score is mirrored back onto `content_items.quality_score`.
- The computed verdict gates the parent item: passing checks move the item toward client review, while weaker checks hold it in `internal_review`.
- Reviewers can read quality checks through the collection endpoints.
- Manager access is required to create quality checks.

## Verification
- `tests/test_packet168.py`
- full API regression after the packet
