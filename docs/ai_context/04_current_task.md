# Current task

## Task ID
content-generation-output-contract-packet-c3

## Status
Completed.

## What shipped
- `apps/worker/app/role_prompts.py` now includes brand tone/positioning, allowed/forbidden claims, product facts, audience pains/goals/objections, channel, and goal in `build_role_user_prompt(...)`.
- `COMMON_SYSTEM_PROMPT` now enforces the provided-context-only rule, no invented facts, and `forbidden_claims` compliance.
- Final-stage worker output now targets `content_version.structured_json` with `{title, text, short_text, cta, visual_task, image_prompt, risks}` plus `body_markdown`.
- `apps/api/app/api/v1/jobs.py` now parses final content-generation JSON into `structured_json` and stores `body_markdown` separately on `content_versions`.
- Added `apps/api/tests/test_packet208.py` to cover structured output persistence.
- Expanded `apps/worker/tests/test_role_prompts.py` to cover the full context-rich prompt and final output contract.

## Verification
- `uv run pytest -q tests/test_packet207.py tests/test_packet208.py`
- `uv run pytest -q tests/test_role_prompts.py`
- `uv run pytest -q` in `apps/api`
- `uv run pytest -q` in `apps/worker`

## Next packet
- Wait for the next user-directed step after deploy / live verification if requested.
