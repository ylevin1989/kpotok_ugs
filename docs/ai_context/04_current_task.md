# Current task

## Task ID
admin-audit-packet-b

## Status
Completed.

## What shipped
- Added `audit_logs` plus Alembic migration `20260707_028_create_audit_logs_table.py`.
- Added catch-up migration `20260707_029_create_organization_permission_events_table.py` so live Postgres matches the already-used permission-event model.
- Added `app/domain/audit.py::record_audit(...)` as the shared write helper for platform-sensitive actions.
- Wired audit writes into:
  - organization membership role changes
  - organization status changes
  - subscription upserts
  - admin job retry / cancel actions
- Added `app/api/v1/admin.py` with platform-admin-only routes:
  - `GET /api/v1/admin/clients`
  - `GET /api/v1/admin/jobs`
  - `POST /api/v1/admin/jobs/{id}/retry`
  - `POST /api/v1/admin/jobs/{id}/cancel`
  - `GET /api/v1/admin/tickets`
  - `GET /api/v1/admin/content-review`
  - `GET /api/v1/admin/usage`
  - `GET /api/v1/admin/audit-logs`
- Added test coverage in `tests/test_packet205.py` and extended the Postgres critical-path lane to include it.
- Kept `PlatformRole` unchanged in this packet: `developer` was intentionally not added yet.

## Verification
- `uv run pytest -q tests/test_packet205.py`
- `uv run pytest -q tests/test_packet200.py tests/test_packet204.py tests/test_packet205.py`
- `uv run pytest -q`
- `bash scripts/run_postgres_critical_path.sh`
- `docker compose build cf-api`
- `docker compose up -d --force-recreate cf-api`
- `docker exec cf-api alembic current` -> `20260707_029 (head)`
- `curl -i https://apiha.uno-ai.pw/api/v1/health`
- Live public API smoke for admin/audit packet: register users -> create org -> add/update member -> upsert subscription -> pause org -> seed ticket/job/review/usage -> verify `/api/v1/admin/*` -> cancel/retry jobs -> confirm new audit actions -> confirm owner gets `403`

## Next packet
- Wait for the next user-directed roadmap step after deploy verification.
