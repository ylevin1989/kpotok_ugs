# Handoff

## Summary for the next packet
- Exports Packet 01 is live on the public API.
- `exports` now persists tenant-scoped export artifacts with `markdown`, `csv`, and `zip` formats.
- Download reads back from MinIO using keys under `organizations/{org}/brands/{brand}/exports/{id}/...`.
- Only `approved` content items and their current content versions are included in artifacts.
- The live schema is at Alembic head `20260707_027` and `cf-api` keeps auto-applying migrations on startup via `infra/docker/api-entrypoint.sh`.

## Do next
- Keep future export work additive on top of the `exports` table and API surface.
- Preserve strict tenant scoping on every future export filter and download path.
- Reuse the Postgres critical-path lane when extending export behavior.

## Do not do
- Do not remove the `cf-api` entrypoint-based `alembic upgrade head` startup flow.
- Do not include non-approved content versions in exported artifacts.
- Do not write export files outside the organization/brand/id-scoped MinIO key prefix.
