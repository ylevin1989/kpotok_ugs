# Current task

## Task ID
phase_51_content_plan_generation_stage3

## Status
Completed.

## What shipped
- `apps/api/app/schemas/content_plan.py` adds `ContentPlanGenerate` for date-range generation requests
- `apps/api/app/api/v1/content_plans.py` adds `POST /api/v1/content-plans/generate` and derives titles from brand/product/audience DNA context
- `apps/api/tests/test_packet196.py` covers successful generation, inclusive date expansion, and product-scope validation
- `docs/content-plans.md` documents the generation endpoint and date-range behavior

## Verification
- `uv run pytest -q tests/test_packet196.py` in `apps/api` passes
- `uv run pytest -q` in `apps/api` passes
- `npm run build` in `apps/web` passes and includes `/content-plans`

## Next packet
Proceed to stage4-export-monetization: export, subscriptions, usage accounting, and limit enforcement
