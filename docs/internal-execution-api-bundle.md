# Internal execution API bundle

This bundle is the public entry point for client integrators who need the internal execution role contract.

## What to read first

1. [`docs/internal-roles.md`](internal-roles.md)
   - canonical internal role registry
   - supported execution profiles
   - role purposes and ordering

2. [`docs/jobs-api-reference.md`](jobs-api-reference.md)
   - `execution_profile` request field
   - `internal_role_plan` response field
   - create/read examples for the public API

## Public contract summary

### `execution_profile`
- Optional on `POST /api/v1/jobs`
- Defaults to `general_content` when omitted
- Selects the ordered internal role chain used by the worker
- The dashboard create form now exposes the same supported profile set for operator selection
- The public dashboard also shows the canonical profile reference alongside the job-specific resolved plan

### `internal_role_plan`
- Returned by `GET /api/v1/jobs`
- Returned by `GET /api/v1/jobs/{job_id}`
- Each item includes `role_id`, `label`, and `purpose`
- Order is significant and matches the execution chain

## Supported profiles

| execution_profile | ordered internal roles |
| --- | --- |
| `general_content` | `mike` → `emma` → `iris` → `alex` → `david` |
| `seo_content` | `mike` → `emma` → `iris` → `sarah` → `alex` → `david` |
| `ads_content` | `mike` → `emma` → `iris` → `adrian` → `alex` → `david` |
| `architecture_support` | `mike` → `bob` → `david` |

## Source of truth

- `apps/api/app/domain/internal_agent_roles.py`
- `apps/api/app/schemas/job.py`
- `apps/api/app/api/v1/jobs.py`
- `apps/worker/app/llm_client.py`
- `apps/worker/app/role_prompts.py`
