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

## 2026-07-07 — Postgres critical-path lane automation
Decision: run the critical-path integration lane from the host workspace against the shared `cf-postgres` service instead of a bind-mounted throwaway test container.

Chosen approach:
- Use the host repo checkout and `uv run pytest` directly.
- Reuse the already-running shared Postgres service (`cf-postgres`) for the lane DB.
- Source credentials from the container environment instead of hardcoding role/password values.

Rationale:
- A bind-mounted throwaway container could not reliably see the workspace checkout in this environment.
- The shared Postgres service is already healthy and matches the runtime the app uses locally.
- This keeps the lane reproducible without depending on an extra ephemeral container layer.

Implication:
- Keep future critical-path automation host-based unless the Docker workspace-mount behavior is revisited.
- Do not assume `postgres` is the DB role; read the running service’s env when wiring automation.

## 2026-07-07 — Exports Packet 01 contract
Decision: ship exports as synchronous, persisted artifacts instead of inline-only responses, while keeping export contents restricted to approved current versions within the caller's org/brand scope.

Chosen approach:
- Persist an `exports` row first with `pending` status, then render and upload the artifact synchronously.
- Support three artifact formats: `markdown`, `csv`, and `zip`.
- Store artifacts in MinIO at `organizations/{org}/brands/{brand}/exports/{export_id}/...`.
- Scope every export query and download by organization membership plus the export's own `organization_id` and `brand_id`.

Rationale:
- The product needs auditable export records and repeatable downloads rather than one-off transient payloads.
- Tenant-safe MinIO prefixes keep artifact storage boundaries aligned with API scope checks.
- Restricting exports to approved current versions matches the review gate and prevents stale or draft content leakage.

Implication:
- Future export extensions should stay additive on the `exports` table/API rather than replacing the persisted artifact contract.
- Download handlers must reject artifact keys outside the export's expected tenant prefix.
- Any future async export pipeline must preserve the same approved-only and tenant-scoped output rules.

## 2026-07-13 — content-generation context propagation
Decision: carry rich content-generation context through the existing brief/job contract, then surface the same brief payload in `JobRead` and the worker role prompt.

Chosen approach:
- Build the generation context in `Brief.content` as a nested JSON payload with brand, product, audience, channel, and task sections.
- Expose `brief_content` in the job read model so worker clients do not need a separate brief fetch before executing.
- Inject the brief payload directly into the worker role prompt so the LLM sees the actual context instead of only IDs and the job title.

Rationale:
- The brief is already the canonical content-generation handoff object, so enriching it keeps the pipeline consistent.
- Adding the content to `JobRead` avoids an extra API round-trip in the worker path.
- Prompt-time injection makes the context available to the model without duplicating domain lookups in the worker.

Implication:
- Future generation packets should keep the brief payload as the source of truth for LLM context.
- If new context sections are added later, they should be appended to the same brief payload and surfaced through the same job-read contract.
- Worker prompt changes should prefer consuming the brief payload rather than re-deriving the same information from multiple endpoints.

## 2026-07-07 — Admin + Audit Packet B contract
Decision: add a single platform-facing admin surface plus a shared `audit_logs` table for sensitive write actions, but do not add `PlatformRole.developer` in this packet.

Chosen approach:
- Introduce `audit_logs` as a general platform audit table with `actor_user_id`, nullable `organization_id`, `action`, `entity_type`, `entity_id`, `metadata_json`, and optional `ip`.
- Use a shared `record_audit(...)` helper instead of route-local logging logic.
- Audit only sensitive writes in this packet: membership role changes, organization status changes, subscription upserts, and manual admin job retry/cancel.
- Expose a platform-admin-only `/api/v1/admin` surface for clients, jobs, tickets, internal-review content, usage, and audit-log readback.
- Keep access restricted to existing `super_admin` / `platform_admin` roles; defer `developer` until a separate read-only permission matrix is explicitly designed.

Rationale:
- The platform needs one place to inspect cross-tenant operational state and one durable audit stream for operator-sensitive writes.
- Reusing one helper keeps future audit expansion consistent and avoids fragmented per-route implementations.
- Adding `developer` now would widen the platform role contract without a settled read-only boundary, which is riskier than deferring it.

Implication:
- Future sensitive platform writes should call `record_audit(...)` instead of inventing new audit storage.
- Read/list endpoints remain non-audited unless a later requirement explicitly changes that policy.
- If `developer` is introduced later, it should be additive and read-only by default rather than piggybacking on `require_platform_admin`.
