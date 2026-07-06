# Decisions

## 2026-07-04 — architecture direction

Decision: return to the original Content Factory architecture from the TЗ.

Chosen direction:
- Docker Agent Manager
- Hermes-agent per client
- Redis + BullMQ

Rationale:
- The current Postgres-backed job/worker path diverged from the product spec.
- Product value should be built on the domain layer first, not further on queue/auth perimeter work.
- The decision was explicitly confirmed by the owner in this session.

Constraints now in effect:
- Freeze further `jobs` table expansion.
- Freeze additional org/membership role work until product-domain layers exist.
- Start the next implementation packet from `products` and `scope`.

Update 2026-07-06:
- The content-generation bridge now reuses the existing brief/job pipeline instead of expanding the `jobs` table.
- `content_items/{id}/generate` creates a generation brief + queued job, and job completion persists the resulting `content_version` back onto the item.
- Brand and product DNA are now stored as JSON snapshots on the existing brand/product records and are generated through the same brief/job pipeline.
- Ticket revision processing now reuses the same pipeline: `request-revision` creates a ticket, `tickets/{id}/process` creates a queued revision job, and completion writes a new content version plus resolves the ticket.
- Quality checks are now computed from the actual content/body plus brand and product context; the result drives the item toward client review or keeps it in `internal_review`.
- Existing content versions can now be promoted back to current through `POST /api/v1/content-versions/{content_version_id}/promote`.

## 2026-07-06 — Hermes vs OpenRouter architecture
Decision: treat Hermes and OpenRouter as different layers, not competing runtimes.

Chosen boundary:
- Hermes = agent runtime, orchestration, memory, skills, tools, gateway, profiles, and task execution.
- OpenRouter = inference provider layer behind Hermes's provider abstraction.
- Per-client isolation, when needed, lives in Hermes profiles/processes/containers — not in a separate OpenRouter-only app.

Rationale:
- Hermes provides the orchestration and tool surface that OpenRouter does not.
- OpenRouter is useful for model access, routing, and fallback, but it does not replace the agent runtime.
- This keeps the app boundary explicit: runtime decisions stay in Hermes; model/provider decisions stay in provider config.

Implication:
- Do not redesign the product as "OpenRouter instead of Hermes".
- Do expose provider choice and fallback/routing at the model boundary.
- Keep the existing Hermes/OpenRouter integration documented as a runtime/provider split, not a product fork.
