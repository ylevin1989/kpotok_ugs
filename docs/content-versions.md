# Content versions

`content_versions` stores append-only revisions for a content item.

## Contract

| Field | Meaning |
|---|---|
| `organization_id` | Owning organization. |
| `content_item_id` | Parent content item. |
| `version_number` | Monotonic version number within the item. |
| `body_markdown` | Render-ready markdown body. |
| `structured_json` | Structured payload for downstream renderers. |
| `change_summary` | Short human-readable diff summary. |
| `generation_type` | How this version was produced. |
| `generated_from_task_id` | Optional Hermes task source. |
| `created_by` | Creator user id when available. |
| `is_current` | Marks the active version. |
| `created_at` | Creation timestamp. |
| `updated_at` | Last update timestamp. |

## Generation types
- `initial`
- `revision`
- `manual_edit`
- `quality_fix`

## Behavior
- Only one version should be current per content item.
- Creating a current version demotes prior current versions.
- `content_item.current_version_id` follows the current version.
- Existing versions can be promoted back to current through `POST /api/v1/content-versions/{content_version_id}/promote`.
