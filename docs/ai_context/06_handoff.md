# Handoff

## Summary for the next packet
- Content-generation context propagation is now implemented end-to-end for the current packet.
- `Brief.content` carries the rich nested generation payload, `JobRead` now surfaces `brief_content`, and the worker role prompt injects that payload for the LLM.
- Scope mismatch on product-scoped generation is covered by tests and returns `409`.
- Full API/worker regression is green after the packet.

## Do next
- Continue with the next user-directed packet only after deploy / live verification if requested.
- Keep future generation packets appending context to the same brief/job contract rather than reintroducing ID-only handoffs.

## Do not do
- Do not fall back to ID-only prompts for content generation.
- Do not add a separate parallel context store unless the user explicitly requests an architectural change.
