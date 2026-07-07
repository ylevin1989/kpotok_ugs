# Handoff

## Summary for the next packet
- Admin + Audit Packet B is deployed and live-verified on the public API.
- Live schema is now at Alembic head `20260707_029`; migration `029` backfills the previously-missing `organization_permission_events` table used by the org membership/status audit path.
- `audit_logs` is the new canonical platform audit table for sensitive write actions across org role/status changes, subscription changes, and admin job retry/cancel.
- `GET /api/v1/admin/*` now gives platform admins readback across clients, jobs, tickets, internal-review content, usage, and audit logs.
- `PlatformRole.developer` was intentionally not added in this packet; the platform-only admin surface remains restricted to `super_admin` and `platform_admin`.

## Do next
- Keep future admin packets additive on the `/api/v1/admin` surface.
- Reuse `record_audit(...)` for any new sensitive platform write action.
- If `developer` is introduced later, define a separate read-only permission matrix instead of silently broadening `require_platform_admin`.

## Do not do
- Do not replace `audit_logs` with ad-hoc per-route logging.
- Do not log read-only admin/list endpoints into `audit_logs`.
- Do not broaden platform-admin routes to client roles.
