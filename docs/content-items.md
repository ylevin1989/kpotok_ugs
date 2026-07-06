# Content items

`content_items` is the execution-ready layer under `content_plans`.

## Contract

| Field | Meaning |
|---|---|
| `organization_id` | Owning organization. |
| `brand_id` | Owning brand scope. |
| `product_id` | Optional product scope; required when `scope = product`. |
| `content_plan_id` | Parent content plan. |
| `audience_segment_id` | Optional linked audience segment. |
| `scope` | One of `brand`, `product`, `campaign`, `comparison`. |
| `platform` | Publishing platform or channel. |
| `content_type` | Content format or type. |
| `goal` | Goal or objective for the item. |
| `title` | Human-readable title. |
| `status` | Lifecycle status. |
| `quality_score` | Integer score from 0 to 100. |

## Rules

- `scope = product` requires `product_id`.
- `content_plan_id` must belong to the same organization and brand.
- `product_id` and `audience_segment_id`, when provided, must belong to the same organization and brand.
- `quality_score` is constrained to `0..100`.
- Archived organizations are read-only for item creation.
- `POST /api/v1/content-items/{content_item_id}/generate` creates a queued generation job; when that job completes, the resulting output is persisted as a new `content_version`, auto-quality-checked, and then either released toward client review or held in `internal_review`.
- `POST /api/v1/content-items/{content_item_id}/request-revision` creates a revision ticket; processing that ticket creates a queued revision job that writes a new `content_version` when completed, then auto-runs a quality check that either releases the item toward client review or holds it in `internal_review`.

## API

- `POST /api/v1/content-items`
- `POST /api/v1/content-items/{content_item_id}/generate`
- `GET /api/v1/content-items`
- `GET /api/v1/content-items/{content_item_id}`

## Example

```json
{
  "organization_id": "2d5f8d18-0000-0000-0000-000000000001",
  "brand_id": "2d5f8d18-0000-0000-0000-000000000002",
  "product_id": "2d5f8d18-0000-0000-0000-000000000003",
  "content_plan_id": "2d5f8d18-0000-0000-0000-000000000004",
  "audience_segment_id": "2d5f8d18-0000-0000-0000-000000000005",
  "scope": "product",
  "platform": "instagram",
  "content_type": "post",
  "goal": "Drive launch awareness",
  "title": "Rocket Tea launch reel",
  "status": "draft",
  "quality_score": 87
}
```
