# Handoff

## Summary for the next packet
- Claim-time generation context propagation is now implemented end-to-end for the current packet.
- `JobRead` now exposes both `brief_content` and parsed `context`, and the worker role prompt prefers `context` when it is available.
- `claim-next` and `claim` are covered by tests so workers receive the real generation payload at claim time.
- Full API and worker regression is green after the packet.

## Do next
- Continue with the next user-directed packet only after deploy / live verification if requested.
- Keep future generation packets appending context to the same brief/job contract rather than reintroducing ID-only handoffs.

## Do not do
- Do not fall back to ID-only prompts for content generation.
- Do not add a separate parallel context store unless the user explicitly requests an architectural change.
