# Current task

## Task ID
content-generation-context-packet-c1

## Status
Completed.

## What shipped
- `app/domain/content_generation.py` now resolves rich generation context from the database and serializes it into a nested brief payload with:
  - `brand_context`
  - `product_context`
  - `audience_context`
  - `channel`
  - `task`
- `app/api/v1/content_items.py` now passes `db` into the brief-content builder.
- `app/schemas/job.py` and `app/api/v1/jobs.py` now expose `brief_content` alongside `brief_id` in `JobRead` so workers receive the actual brief payload, not just the reference ID.
- `apps/worker/app/role_prompts.py` now injects `brief_content` into the role prompt so the LLM sees the generated context.
- Added `tests/test_packet206.py` for the rich context builder and scope mismatch guard.
- Added/updated worker prompt coverage in `apps/worker/tests/test_role_prompts.py`.

## Verification
- `uv run pytest -q tests/test_packet206.py`
- `uv run pytest -q tests/test_role_prompts.py`
- `uv run pytest -q`

## Next packet
- Wait for the next user-directed roadmap step after deploy verification.
