# Current task

## Task ID
claim-time-generation-context-packet-c2

## Status
Completed.

## What shipped
- `apps/api/app/schemas/job.py` now includes `context: dict[str, Any] | None` on `JobRead`.
- `apps/api/app/api/v1/jobs.py` now fills `context` from parsed `Brief.content` so `claim-next`, `claim`, and other job readbacks expose the generation payload.
- `apps/worker/app/role_prompts.py` now prefers `context` and falls back to `brief_content` when building the role prompt.
- Added `apps/api/tests/test_packet207.py` to cover claim-time context propagation through `claim-next` and `claim`.
- Expanded `apps/worker/tests/test_role_prompts.py` to prove the worker prompt prefers the parsed generation context.

## Verification
- `uv run pytest -q tests/test_packet207.py`
- `uv run pytest -q tests/test_role_prompts.py`
- `uv run pytest -q`

## Next packet
- Wait for the next user-directed step after deploy and live verification.
