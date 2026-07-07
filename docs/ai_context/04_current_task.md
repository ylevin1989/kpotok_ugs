# Current task

## Task ID
exports-packet01

## Status
Completed.

## What shipped
- Added the `exports` domain model plus Alembic migration `20260707_027_create_exports_table.py`.
- Added `app/api/v1/exports.py` with:
  - `POST /api/v1/content-plans/{id}/export`
  - `POST /api/v1/exports`
  - `GET /api/v1/exports`
  - `GET /api/v1/exports/{id}`
  - `GET /api/v1/exports/{id}/download`
- Export generation is synchronous and tenant-scoped by `organization_id` + `brand_id`.
- Only `approved` content items are exported, and each export reads the current content version payload (`body_markdown` / `structured_json`).
- Markdown, CSV, and ZIP artifacts are stored in MinIO under `organizations/{org}/brands/{brand}/exports/{id}/...`.
- The API Docker entrypoint auto-applied migration `027` during deploy and the live public API export flow was re-verified after rollout.

## Verification
- `uv run pytest -q tests/test_packet204.py`
- `uv run pytest -q`
- `bash scripts/run_postgres_critical_path.sh`
- `docker compose build cf-api`
- `docker compose up -d --force-recreate cf-api`
- `curl -i https://apiha.uno-ai.pw/api/v1/health`
- Live public API proof: register → org → brand → content plan → content item → content version → approve → export → download

## Next packet
- Wait for the next user-directed roadmap step.
