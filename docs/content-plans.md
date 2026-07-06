# Content plans

`content_plans` is the planning surface for the content calendar. It sits above `products`, `media_assets`, and `audience_segments`, and below the future generation/material surfaces.

## Contract

| Field | Meaning |
|---|---|
| `organization_id` | Owning organization. |
| `brand_id` | Owning brand scope. |
| `product_id` | Optional product scope; required when `scope = product`. |
| `audience_segment_id` | Optional linked audience segment. |
| `scope` | One of `brand`, `product`, `campaign`, `comparison`. |
| `date` | Planned publishing date. |
| `title` | Human-readable plan title. |
| `platform` | Channel or platform for the planned item. |
| `content_type` | Planned content format. |
| `goal` | Planning goal or campaign objective. |
| `status` | Lifecycle status of the plan. |

## Rules

- `scope = product` requires `product_id`.
- `product_id` must belong to the same organization and brand.
- `audience_segment_id`, when provided, must belong to the same organization and brand.
- Archived organizations are read-only for plan creation.
- `POST /api/v1/content-plans/generate` creates one row per date in the inclusive `start_date`/`end_date` range and mixes in Brand/Product DNA context when available.

## API

- `POST /api/v1/content-plans`
- `POST /api/v1/content-plans/generate`
- `GET /api/v1/content-plans`
- `GET /api/v1/content-plans/{content_plan_id}`

## Example

```json
{
  "organization_id": "2d5f8d18-0000-0000-0000-000000000001",
  "brand_id": "2d5f8d18-0000-0000-0000-000000000002",
  "product_id": "2d5f8d18-0000-0000-0000-000000000003",
  "audience_segment_id": "2d5f8d18-0000-0000-0000-000000000004",
  "scope": "product",
  "date": "2026-07-05",
  "title": "Rocket Tea launch week",
  "platform": "instagram",
  "content_type": "post",
  "goal": "Drive launch awareness",
  "status": "draft"
}
```

`content_items` is the next phase after this packet.
