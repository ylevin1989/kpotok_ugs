# Jobs API reference

This reference covers the additive job fields used by the internal execution role pipeline.

## Core fields

### `execution_profile`
Optional input on `POST /api/v1/jobs`.

If omitted, the API defaults to `general_content`.

The public dashboard create form exposes the same supported profiles for operator selection.

Supported profiles:

| execution_profile | ordered internal roles |
|---|---|
| `general_content` | `mike` → `emma` → `iris` → `alex` → `david` |
| `seo_content` | `mike` → `emma` → `iris` → `sarah` → `alex` → `david` |
| `ads_content` | `mike` → `emma` → `iris` → `adrian` → `alex` → `david` |
| `architecture_support` | `mike` → `bob` → `david` |

### `internal_role_plan`
Returned by `GET /api/v1/jobs` and `GET /api/v1/jobs/{job_id}`.

Each item contains:
- `role_id`
- `label`
- `purpose`

The order is significant and matches the worker execution chain.

### `execution_trace.validation_result`
Terminal validation summary returned by `GET /api/v1/jobs/{job_id}`.

It is populated when the job reaches a terminal validation outcome:
- completed with a valid artifact key → `status=validated`, `artifact_scope_status=validated`, `artifact_key=<tenant-scoped key>`
- artifact scope rejection → `status=rejected`, `artifact_scope_status=rejected`, `reason=<worker error>`, `failure_code=artifact_scope_rejection`

This mirrors the same structured payload attached to the terminal trace event.

### `execution_trace.trace_compact_summary`
Operator-facing compact summary returned by `GET /api/v1/jobs/{job_id}`.

It is a flattened readback of the current trace state and includes fields such as:
- `current_stage`
- `final_status`
- `attempt_number`
- `dominant_stage_name`
- `heartbeat_count`
- `reclaim_count`
- `progress_span_percent`
- `last_stage_label`
- `average_progress_percent`
- `unique_transition_tag_count`
- `worker_count`
- `worker_metadata_key_count`
- `latest_worker_metadata_keys`

This view is intended for dashboard/operator inspection rather than worker control.

## Example: create job

```json
{
  "organization_id": "2c2cc8f8-7d0c-4f39-9f97-f3d3f3d8b301",
  "brand_id": "b8b0d9ef-7f5c-45d0-a8f4-46c3dc4fcb73",
  "brief_id": "7f0d9d3f-f2f2-4f10-b9ea-2e4ad19f5d42",
  "title": "SEO content job",
  "execution_profile": "seo_content"
}
```

## Example: read job

```json
{
  "id": "f9a3a1f3-7d59-4a2c-9f17-7f6a9e3f8d4e",
  "title": "SEO content job",
  "execution_profile": "seo_content",
  "internal_role_plan": [
    {
      "role_id": "mike",
      "label": "Mike",
      "purpose": "Internal production manager who routes tasks and frames execution order."
    },
    {
      "role_id": "emma",
      "label": "Emma",
      "purpose": "Product manager who protects product meaning and desired outcome."
    },
    {
      "role_id": "iris",
      "label": "Iris",
      "purpose": "Researcher who derives market, ICP, pains, and trend inputs."
    },
    {
      "role_id": "sarah",
      "label": "Sarah",
      "purpose": "SEO specialist who shapes organic search angles and keyword intent."
    },
    {
      "role_id": "alex",
      "label": "Alex",
      "purpose": "Content constructor who assembles drafts, scripts, and visual/content briefs."
    },
    {
      "role_id": "david",
      "label": "David",
      "purpose": "Data analyst who reviews consistency, deviations, and efficiency signals."
    }
  ]
}
```

## Source of truth
- `apps/api/app/domain/internal_agent_roles.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/api/v1/jobs.py`
- `apps/worker/app/llm_client.py`
- `apps/worker/app/role_prompts.py`
