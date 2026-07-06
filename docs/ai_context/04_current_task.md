# Current task

## Task ID
stage4-export-monetization

## Status
Completed.

## What shipped
- `apps/api/app/db/models/subscription.py` and `apps/api/app/db/models/usage_record.py` add billing/usage persistence
- `apps/api/app/domain/billing.py` centralizes monthly limit enforcement and usage recording
- `apps/api/app/api/v1/subscriptions.py` exposes subscription list/create and usage read endpoints
- `apps/api/app/api/v1/content_plans.py` now supports export plus monthly limit checks for generation/export
- `apps/api/tests/test_packet197.py` covers subscriptions, usage accounting, export, and limit blocking
- `apps/web/app/subscriptions/page.tsx` provides the subscription management UI
- `apps/web/app/content-plans/page.tsx` adds export support

## Verification
- `uv run pytest -q tests/test_packet197.py` in `apps/api` passes
- `uv run pytest -q` in `apps/api` passes
- `npm run build` in `apps/web` passes and includes `/subscriptions`

## Next packet
Continue with the next roadmap item after export/subscriptions monetization is complete.
