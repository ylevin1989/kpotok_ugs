# Handoff

## Summary for the next packet
- Content-generation prompt enrichment is now implemented end-to-end.
- `build_role_user_prompt(...)` carries the full content brief context: brand tone/positioning, allowed/forbidden claims, product facts, audience pains/goals/objections, channel, and goal.
- `COMMON_SYSTEM_PROMPT` now enforces provided-context-only generation and `forbidden_claims` compliance.
- Final-stage worker outputs now map to `content_version.structured_json` with `body_markdown` stored separately.
- API and worker regressions are green after the packet.

## Do next
- Continue with the next user-directed packet only after deploy / live verification if requested.
- Keep future generation packets appending context to the same brief/job contract rather than reintroducing thin prompts.

## Do not do
- Do not fall back to ID-only prompts for content generation.
- Do not add a separate parallel context store unless the user explicitly requests an architectural change.
