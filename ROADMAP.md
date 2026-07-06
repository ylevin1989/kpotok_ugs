# Content Factory Roadmap

## Project role
Content Factory is the control plane and application layer built on top of an existing Hermes runtime. Its job is to provide a production-backed multi-organization product surface with clear org boundaries, membership roles, brand scoping, and later workflow/content execution on top of that foundation.

## Current status
### Production foundation — done
- Production routing works via Traefik
- Public domains are live:
  - `app.uno-ai.pw`
  - `apiha.uno-ai.pw`
  - `ha.uno-ai.pw` kept untouched for the existing Hermes runtime
- Server PostgreSQL is connected and used by the app
- Docker services (`cf-api`, `cf-worker`, `cf-web`, `cf-redis`, `cf-minio`) are running in the shared host environment
- Migrations are working against the live database

### Domain foundation — done
- Organizations CRUD baseline is implemented
- Membership management exists: list, add, update, delete
- Brands CRUD baseline exists
- Reviewer/manager/owner role model is live
- Archived organizations are enforced as read-only for key write paths
- Owner-sensitive membership operations are fully matrix-modeled through create/update/delete helpers
- Organization membership role policy reference document exists for the current production rules
- Organization status lifecycle policy is formalized through archive/unarchive semantics: manager can edit metadata only on writable orgs, owner controls status transitions, and owner-only status-only unarchive is allowed from archived

### Content Generation Bridge Packet 01 — done
- `apps/api/app/api/v1/content_items.py` now exposes `POST /api/v1/content-items/{content_item_id}/generate`
- `apps/api/app/api/v1/jobs.py` now converts completed generation jobs into `content_versions` and marks the parent `content_item` as generated
- `apps/api/tests/test_packet176.py` covers the end-to-end generate → claim → complete → version persistence path
- API regression remains green after the content-generation bridge packet

### Brand/Product DNA Packet 01 — done
- `apps/api/app/api/v1/brands.py` and `apps/api/app/api/v1/products.py` now expose `generate-dna` routes
- `apps/api/app/api/v1/jobs.py` now persists brand/product DNA JSON onto the target record when the DNA job completes
- `apps/api/tests/test_packet177.py` covers brand and product DNA generation + persistence
- API regression remains green after the DNA packet

### Ticket Revision Packet 01 — done
- `apps/api/app/api/v1/tickets.py` now exposes `POST /api/v1/tickets/{ticket_id}/process`
- `apps/api/app/api/v1/jobs.py` now turns completed ticket-processing jobs into a new `content_version` and resolves the ticket
- `apps/api/tests/test_packet178.py` covers revision-ticket processing, version rollover, ticket resolution, and the resulting quality gate
- API regression remains green after the ticket-revision packet

### Quality Check Packet 01 — done
- `apps/api/app/api/v1/quality_checks.py` now computes quality scores from actual content plus brand/product context and gates the parent item
- `apps/api/app/api/v1/jobs.py` now auto-runs quality checks after generated content versions are persisted
- `apps/api/tests/test_packet168.py` covers computed quality-check API behavior and gating
- `apps/api/tests/test_packet176.py` / `apps/api/tests/test_packet178.py` expect gated statuses after generation and revision completion
- `apps/api/tests/test_packet179.py` covers generation-time auto quality-check gating end-to-end
- API regression remains green after the quality-check packet

### MVP Track 01–08 — done
Goal completed: stop the trace-first drift, replace the web stub with the first real product-facing auth shell, add the first persistent organization/brand scope selection layer, ship the first brief create/list happy path, expose jobs create/list/detail/status flows on top of the already-running backend/API, surface completed job results/artifacts directly in the public dashboard, align dashboard write affordances with existing reviewer vs manager/owner API permissions, and normalize the first production-safe soft-delete vs hard-delete rule for brand deletion.

Delivered scope:
- Roadmap focus is explicitly shifted from deeper execution-trace enrichment to MVP-first web delivery
- Further additive trace-contract expansion is now treated as post-MVP work unless it blocks the product flow
- API now serves browser-safe CORS preflight for the real app origin `https://app.uno-ai.pw`
- `apps/web` is no longer a stub: `/` redirects based on session state, `/login` performs live auth, and `/dashboard` reads the real authenticated profile via `/api/v1/auth/me`
- The web shell stores a minimal local browser session and now persists the selected organization/brand scope for upcoming brief/job screens
- Dashboard now reads real organizations from `/api/v1/organizations`, real brands from `/api/v1/brands?organization_id=...`, real briefs from `/api/v1/briefs`, and real jobs from `/api/v1/jobs`
- Dashboard can now create a brief in the selected scope, create a job from the selected brief, render the resulting live job list, and load selected job detail/status via `/api/v1/jobs/{job_id}`
- Dashboard now exposes `output_text`, authenticated artifact download, textual artifact preview, and persisted artifact metadata directly in the selected job panel
- Reviewer scope is now explicitly read-only in the dashboard: create-brief/create-job affordances are replaced with explanatory notices, while manager/owner retain write forms
- Live API job readbacks now normalize legacy `execution_trace` payloads so older completed jobs still render in `/api/v1/jobs` and in the public dashboard instead of failing response-model validation
- Brand deletion is now explicitly split by data shape: empty brands remain hard-deletable, while brands that already carry briefs/jobs return `409` instead of cascading destructive deletes
- Public `cf-web` now runs in production mode (`next start`) instead of a dev/HMR runtime
- Public `cf-api` now runs as a plain production `uvicorn` process without `--reload`/watchfiles reloader semantics
- Public reviewer live-smoke is now covered with a real browser session proving read-only affordances against the public app/API
- Existing Packet 05–149 backend/runtime work remains intact: multi-tenant org/brand foundation, briefs/jobs APIs, worker lifecycle, artifact persistence/readback, and deep execution traces for later product surfaces
- Verification now includes web production-readiness build checks, full API regression, live API artifact readback, live browser-context create/list/detail/result/artifact checks against the public app/API, and public empty-vs-populated brand delete proof
- ROADMAP is updated through MVP-08

### Post-MVP Phase 01 / Internal Roles Packet 01 — done
Goal completed: add the first canonical internal executor-role contract on top of the existing Hermes-backed job system, without turning internal roles into user accounts and without duplicating the Hermes runtime.

Delivered scope:
- Canonical internal role registry now exists in `apps/api/app/domain/internal_agent_roles.py`
- Initial execution profiles are defined: `general_content`, `seo_content`, `ads_content`, `architecture_support`
- `POST /api/v1/jobs` now accepts optional `execution_profile`
- Jobs now persist additive internal execution metadata via `execution_profile` and `internal_role_plan_json`
- `GET /api/v1/jobs` and `GET /api/v1/jobs/{job_id}` now expose `execution_profile` plus ordered `internal_role_plan`
- Default job execution profile is `general_content` when the caller omits the field
- Additive Alembic migration `20260704_013` upgrades the live Postgres schema for the new job fields
- Public live API proof confirms `seo_content` readback with role order `mike -> emma -> iris -> sarah -> alex -> david`
- Full API regression remains green after the additive job contract change

### Post-MVP Phase 01 / Internal Roles Packet 02 — done
Goal completed: make the live worker pipeline role-aware so persisted job traces advance through the canonical internal executor roles instead of generic stub stages.

Delivered scope:
- `apps/worker` now resolves role-aware stages from `internal_role_plan` whenever present and falls back to legacy `worker_process_stages` for older jobs
- Start-of-run lease renewal now records the first internal role stage immediately, so live traces preserve the full ordered role chain instead of skipping the first role
- Worker heartbeats now send `stage_label`, `progress_percent`, `progress_message`, `transition_tag`, and `worker_metadata` for internal role stages
- Public live worker execution now records role-aware trace stages like `role:mike`, `role:emma`, `role:iris`, `role:sarah`, `role:alex`, `role:david`
- Public live trace proof confirms matching `stage_label_summary`, per-role `transition_tag_counts`, and final `last_progress` metadata for the processed job
- Full worker and API regressions remain green after the role-aware execution change

### Post-MVP Phase 01 / Internal Roles Packet 03 — done
Goal completed: surface the resolved internal execution profile and ordered role plan directly inside the public dashboard job detail.

Delivered scope:
- `apps/web/lib/types.ts` now knows `execution_profile` plus ordered `internal_role_plan` items from the live jobs API
- Dashboard job detail now shows a dedicated `Internal execution plan` section in the public UI
- The UI renders both a human-readable execution profile label and the raw profile key for the selected job
- The UI renders the ordered internal role chain with each role's sequence number, label, role id, and purpose
- Public live browser proof confirms the Packet95 role-aware job now shows `Seo Content` plus the ordered role chain from Mike through David in the dashboard
- Web production build and full API regression remain green after the additive dashboard exposure change

### Product Core Packet 01 — done
Goal completed: add the first product-domain entity and CRUD surface scoped by organization and brand, without touching job/membership perimeter work.

Delivered scope:
- `apps/api/app/db/models/product.py` defines the `products` table model with organization/brand scope, product identity fields, list-style product attributes, status, and readiness score
- `apps/api/app/api/v1/products.py` exposes create/list/get endpoints with the same organization/brand access rules used by briefs
- `apps/api/app/schemas/product.py` provides API contracts for product create/read/list responses
- `apps/api/alembic/versions/20260704_014_create_products_table.py` adds the live `products` table and constraints
- `apps/api/app/main.py` and `apps/api/app/db/models/__init__.py` register the new product surface with the running app and metadata
- `apps/api/tests/test_packet160.py` covers the new product CRUD flow, brand/org scoping, and archived organization write blocking
- API regression remains green after the additive product packet

### Product UI Stage 01 — done
Goal completed: lay the first product-facing UI shell on top of the live API and put the repository under git so the work can be tracked safely.

Delivered scope:
- `apps/web/lib/types.ts` adds product domain types for the browser client
- `apps/web/lib/api.ts` adds product API helpers for list/create/update/generate-dna
- `apps/web/app/products/page.tsx` introduces a dedicated product workspace with list, create/edit form, and Product DNA job trigger
- `apps/web/app/dashboard/page.tsx` links to the new products workspace
- `.gitignore` now ignores `.hermes/` and backup artifacts, and the repo is initialized with git
- `npm run build` for `apps/web` succeeds after the product UI additions

### Product UI Stage 02 — done
Goal completed: add the remaining visible product workflow slices so the dashboard can reach the full product workspace set.

Delivered scope:
- `apps/web/lib/types.ts` now includes `ContentScope`, `MediaAsset*`, and `AudienceSegment*` browser contracts
- `apps/web/lib/api.ts` now includes `getMediaAssets`, `createMediaAsset`, `getAudienceSegments`, and `createAudienceSegment`
- `apps/web/app/media-assets/page.tsx` introduces a media library workspace with org/brand/product scope selection and asset creation
- `apps/web/app/audience-segments/page.tsx` introduces an audience segment workspace with org/brand/product scope selection and segment creation
- `apps/web/app/dashboard/page.tsx` links to `/media-assets` and `/audience-segments` in addition to brands/products
- `npm run build` for `apps/web` succeeds after the new workflow slices

### Product Core Packet 02 — done
Goal completed: extend the product surface with update semantics so managers can edit product attributes in place while keeping org/brand scope and uniqueness rules intact.

Delivered scope:
- `apps/api/app/api/v1/products.py` now exposes `PATCH /api/v1/products/{product_id}` and reuses the shared content-write guard
- `apps/api/app/schemas/product.py` adds `ProductUpdate` for partial product edits
- `apps/api/app/api/v1/products.py` now returns `409` for duplicate SKU conflicts on create and update
- `docs/products.md` documents the product contract, scope rules, DNA generation route, and lifecycle guard
- `apps/api/tests/test_packet195.py` covers successful update, archived-organization write blocking, and duplicate SKU rejection
- API regression remains green after the additive product-update packet

### Audience Segments Packet 01 — done
Goal completed: add the first audience segment metadata surface scoped by organization and brand, with product-aware validation and product attachment.

Delivered scope:
- `apps/api/app/db/models/audience_segment.py` defines the `audience_segments` table model with organization/brand scope, optional product attachment, persona metadata, and scope validation guardrails
- `apps/api/app/api/v1/audience_segments.py` exposes create/list/get endpoints and reuses org/brand/product access checks
- `apps/api/app/schemas/audience_segment.py` provides API contracts for audience segment create/read/list responses
- `apps/api/alembic/versions/20260704_016_create_audience_segments_table.py` adds the live `audience_segments` table and constraints
- `apps/api/app/main.py` and `apps/api/app/db/models/__init__.py` register the new audience segment surface with the running app and metadata
- `apps/api/tests/test_packet163.py` covers audience segment CRUD, product-scope validation, and archived organization write blocking
- `docs/audience-segments.md` documents the current audience segment contract and validation rules
- API regression remains green after the additive audience segment packet

### Media Assets Packet 01 — done

Delivered scope:
- `apps/api/app/db/models/media_asset.py` defines the `media_assets` table model with organization/brand scope, optional product attachment, asset metadata, and scope validation guardrails
- `apps/api/app/api/v1/media_assets.py` exposes create/list/get endpoints and reuses org/brand/product access checks
- `apps/api/app/schemas/media_asset.py` provides API contracts for media asset create/read/list responses
- `apps/api/alembic/versions/20260704_015_create_media_assets_table.py` adds the live `media_assets` table and constraints
- `apps/api/app/main.py` and `apps/api/app/db/models/__init__.py` register the new media asset surface with the running app and metadata
- `apps/api/tests/test_packet162.py` covers media asset CRUD, product-scope validation, and archived organization write blocking
- `docs/media-assets.md` documents the current media asset contract and validation rules
- API regression remains green after the additive media asset packet

### Scope Contract Packet 01 — done
Goal completed: add the reusable content scope contract that future generation APIs will use, including the product-only validation rule.

Delivered scope:
- `apps/api/app/domain/content_scope.py` defines the canonical scope values: `brand`, `product`, `campaign`, `comparison`
- `apps/api/app/schemas/scope.py` validates the generation scope payload and requires `product_id` when `scope=product`
- `apps/api/tests/test_packet161.py` covers the helper rule and the schema validation rule
- `docs/scope-model.md` documents the scope contract for future generation endpoints
- API regression remains green after the additive scope contract packet

### Content Plans Packet 01 — done
Goal completed: add the first planning surface on top of products, media assets, and audience segments, with scope-aware validation and brand/product scoping.

Delivered scope:
- `apps/api/app/db/models/content_plan.py` defines the `content_plans` table model with organization/brand scope, optional product + audience segment links, date/platform/content metadata, and scope validation guardrails
- `apps/api/app/api/v1/content_plans.py` exposes create/list/get endpoints and reuses org/brand/product/audience-segment access checks
- `apps/api/app/schemas/content_plan.py` provides API contracts for content plan create/read/list responses
- `apps/api/alembic/versions/20260705_017_create_content_plans_table.py` adds the live `content_plans` table and constraints
- `apps/api/tests/test_packet164.py` covers content-plan CRUD, product-scope validation, audience-segment validation, and archived organization write blocking
- `docs/content-plans.md` documents the current content-plan contract and validation rules
- API regression remains green after the additive content plans packet

### Content Items Packet 01 — done
Goal completed: add the first execution-ready item surface under content plans, with plan linkage, scope-aware validation, and quality scoring.

Delivered scope:
- `apps/api/app/db/models/content_item.py` defines the `content_items` table model with organization/brand scope, optional product + audience segment links, required `content_plan_id`, platform/content metadata, quality score, and scope validation guardrails
- `apps/api/app/api/v1/content_items.py` exposes create/list/get endpoints and reuses org/brand/product/audience-segment/content-plan access checks
- `apps/api/app/schemas/content_item.py` provides API contracts for content item create/read/list responses
- `apps/api/alembic/versions/20260705_018_create_content_items_table.py` adds the live `content_items` table and constraints
- `apps/api/tests/test_packet165.py` covers content-item CRUD, product-scope validation, content-plan linkage validation, audience-segment validation, and archived organization write blocking
- `docs/content-items.md` documents the current content-item contract and validation rules
- API regression remains green after the additive content items packet

### Content Versions Packet 01 — done
Goal completed: add version history beneath content items and expose the current-version link on the item read surface.

Delivered scope:
- `apps/api/app/db/models/content_version.py` defines the `content_versions` table model with version ordering, generation type, optional generated-from-task pointer, and current-version semantics
- `apps/api/app/api/v1/content_versions.py` exposes create/list/get/promote endpoints and keeps `content_items.current_version_id` in sync when a new current version is created or promoted
- `apps/api/app/schemas/content_version.py` provides API contracts for content version create/read/list responses
- `apps/api/alembic/versions/20260705_019_create_content_versions_table.py` adds the live `content_versions` table and constraints
- `apps/api/alembic/versions/20260705_020_add_current_version_id_to_content_items.py` adds the read/write linkage back to the parent item
- `apps/api/tests/test_packet166.py` covers content-version CRUD, current-version rollover, org scoping, and archived organization write blocking
- `docs/content-versions.md` documents the current content-version contract and linkage rules
- API regression remains green after the additive content versions packet

### Approval Tickets Packet 01 — done
Goal completed: add review tickets on top of content versions and expose approve / reject / request-revision actions on content items.

Delivered scope:
- `apps/api/app/db/models/ticket.py` defines the `tickets` table model with organization/brand scope, content item/version linkage, type, reason codes, status, priority, assignment role, creator, and resolution timestamp
- `apps/api/app/api/v1/tickets.py` exposes list/get/create endpoints for tickets
- `apps/api/app/api/v1/content_items.py` now exposes `approve`, `reject`, and `request-revision` actions that create the corresponding ticket records and update item status
- `apps/api/app/schemas/ticket.py` provides API contracts for ticket create/read/list responses plus review-action payloads
- `apps/api/alembic/versions/20260705_021_create_tickets_table.py` adds the live `tickets` table and constraints
- `apps/api/tests/test_packet167.py` covers approve/reject/request-revision, ticket list/get, org access control, and archived organization write blocking
- `docs/tickets.md` documents the current ticket contract and review workflow rules
- API regression remains green after the approval tickets packet

### Quality Checks Packet 01 — done
Goal completed: add content quality checks on top of content versions and review tickets, with manager-triggered QA records and score mirroring back to the content item.

Delivered scope:
- `apps/api/app/db/models/quality_check.py` defines the `quality_checks` table model with org/brand/product scope, content item/version linkage, optional ticket linkage, score, threshold, verdict status, structured checks, issues, recommendations, creator, and check timestamp
- `apps/api/app/api/v1/quality_checks.py` exposes collection read endpoints plus `POST /api/v1/content-items/{content_item_id}/quality-check`
- `apps/api/app/schemas/quality_check.py` provides API contracts for quality-check create/read/list responses
- `apps/api/alembic/versions/20260705_022_create_quality_checks_table.py` adds the live `quality_checks` table and constraints
- `apps/api/tests/test_packet168.py` covers create/list/get, current-version defaulting, org access control, archived-organization blocking, and cross-scope ticket/version rejection
- `docs/quality-checks.md` documents the current quality-check contract and workflow rules
- API regression remains green after the quality checks packet

### Internal Execution API Bundle Packet 01 — done
Goal completed: bundle the public internal-role docs into a public API reference / developer docs bundle so `execution_profile` and `internal_role_plan` are discoverable from one entry point.

Delivered scope:
- `docs/internal-execution-api-bundle.md` provides the public bundle for internal execution roles and job-plan semantics
- `README.md` now links the bundle alongside `docs/internal-roles.md` and `docs/jobs-api-reference.md`
- `apps/api/tests/test_packet169.py` checks the bundle, README link, and roadmap packet marker
- API/docs regression remains green after the internal execution API bundle packet

### Execution Trace Validation Result Packet 01 — done
Goal completed: expose a structured validation_result summary on terminal job trace outcomes so completed and rejected artifact validations are easier to inspect.

Delivered scope:
- `apps/api/app/schemas/job.py` adds `execution_trace.validation_result`
- `apps/api/app/api/v1/jobs.py` populates `validation_result` on completed/rejected terminal traces and mirrors it into terminal event payloads
- `docs/jobs-api-reference.md` documents the validation_result contract
- `apps/api/tests/test_packet170.py` covers completed and rejected validation-result shapes
- API regression remains green after the trace validation-result packet

### Compact Trace Summary Dashboard Packet 01 — done
Goal completed: surface a compact operator-facing trace summary in the public job dashboard so the live readback matches the already-persisted `trace_compact_summary` API field.

Delivered scope:
- `apps/web/lib/types.ts` now exposes `JobExecutionTraceCompactSummaryRead` and a typed `trace_compact_summary` field
- `apps/web/app/dashboard/page.tsx` now renders a compact trace summary block for job detail operator readback
- `apps/api/tests/test_packet181.py` covers the new UI/type contract in source assertions
- `docs/jobs-api-reference.md` now documents the operator-facing compact trace summary view
- Web production build remains green after the dashboard exposure change

### Organization Lifecycle Paused Content Writes Packet 01 — done
Goal completed: make paused organizations read-only for content write endpoints while preserving the existing archived-only behavior for organization/member routes.

Delivered scope:
- `apps/api/app/api/v1/organizations.py` now exposes a content-write guard that blocks paused and archived organizations for content endpoints while preserving archived-only semantics for org/member routes
- `apps/api/app/api/v1/briefs.py`, `brands.py`, `content_plans.py`, `content_items.py`, `content_versions.py`, `media_assets.py`, `audience_segments.py`, `quality_checks.py`, and `tickets.py` now use the content-write guard
- `docs/organization-lifecycle-policy.md` documents the active/paused/archived behavior split
- `apps/api/tests/test_packet171.py` covers paused brief creation and paused brand update blocking
- API regression remains green after the lifecycle packet

### Jobs Claim Next Empty Queue 204 Packet 01 — done
Goal completed: remove empty-queue 404 spam from the worker polling contract by returning 204 No Content from claim-next and treating it as idle in the worker.

Delivered scope:
- `apps/api/app/api/v1/jobs.py` now returns 204 No Content when `POST /api/v1/jobs/claim-next` finds no queued jobs
- `apps/worker/app/api_client.py` and `apps/worker/app/main.py` now treat an empty-queue 204 as an idle poll instead of raising an HTTP error
- `apps/api/tests/test_packet24.py` and `apps/worker/tests/test_packet26_worker.py` cover the new empty-queue contract
- Live deployment verification shows `POST /api/v1/jobs/claim-next` returning 204 and the worker logging idle instead of 404 spam
- API/worker regression remains green after the contract update

### Paused Job Creation Content Guard Packet 01 — done
Goal completed: extend the paused-org content-write guard to job creation so paused organizations cannot enqueue new content work.

Delivered scope:
- `apps/api/app/api/v1/jobs.py` now uses the content-write guard for `POST /api/v1/jobs`
- `docs/organization-lifecycle-policy.md` now lists `jobs.py` among the content-write policy source-of-truth routes
- `apps/api/tests/test_packet172.py` covers paused-job creation blocking
- Live HTTP smoke confirmed paused-org job creation now returns `409` with `Paused organization is read-only for content writes`
- API regression remains green after the paused job-creation packet

### Paused Product Creation Content Guard Packet 01 — done
Goal completed: extend the paused-org content-write guard to product creation so paused organizations cannot create new products.

Delivered scope:
- `apps/api/app/api/v1/products.py` now uses the content-write guard for `POST /api/v1/products`
- `docs/organization-lifecycle-policy.md` now lists `products.py` among the content-write policy source-of-truth routes
- `apps/api/tests/test_packet173.py` covers paused-product creation blocking
- Live HTTP smoke confirmed paused-org product creation now returns `409` with `Paused organization is read-only for content writes`
- API regression remains green after the paused product-creation packet

### Paused Quality Check Content Guard Coverage Packet 01 — done
Goal completed: add regression coverage for the paused-org content-write guard on quality check creation.

Delivered scope:
- `apps/api/tests/test_packet174.py` covers paused quality-check creation blocking
- `docs/organization-lifecycle-policy.md` already lists `quality_checks.py` as part of the content-write policy source of truth; no production code change was needed
- API regression remains green after the coverage-only packet

### Paused Content Item Content Guard Coverage Packet 01 — done
Goal completed: add regression coverage for the paused-org content-write guard on content item creation.

Delivered scope:
- `apps/api/tests/test_packet175.py` covers paused content-item creation blocking
- `docs/organization-lifecycle-policy.md` already lists `content_items.py` as part of the content-write policy source of truth; no production code change was needed
- API regression remains green after the coverage-only packet

Delivered scope:
- `apps/worker` now executes each internal role through an OpenRouter-backed chat completion call instead of the deterministic stub compiler
- Role execution stays inside the existing worker process; no separate runtime was added
- Worker config now reads `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL`, `OPENROUTER_SITE_URL`, and `OPENROUTER_APP_NAME` from environment
- Compiled job output now preserves per-role LLM responses in `role_outputs` and renders them into the final markdown output surface
- Targeted worker tests now cover the OpenRouter request payload plus the role-output compiler seam
- Live verification completed on `Packet05 live LLM role proof` with the worker producing a completed role chain and dashboard-visible result text/artifact
- `cf-worker` was rebuilt and redeployed successfully after the additive LLM executor change
- `apps/api/app/schemas/job.py` now documents `execution_profile` and `internal_role_plan` for OpenAPI consumers
- `docs/internal-roles.md` documents the canonical role registry, execution profiles, and prompting behavior
- `docs/jobs-api-reference.md` documents request/response examples for `execution_profile` and `internal_role_plan`
- `docs/seo-content-role-run-example.md` shows a worked `seo_content` role chain example from Mike through David
- Hermes vs OpenRouter architecture is now explicit in `docs/ai_context/05_decisions.md`: Hermes is the runtime/orchestrator, OpenRouter is the provider layer behind it

## Completed packets
### Packet 05 — done
- Brand delete endpoint
- Reviewer brand read access

### Packet 06 — done
- Organization members list
- Add member
- Update member role

### Packet 07 — done
- Delete member
- Cannot remove own membership
- Cannot remove last owner

### Packet 08 — done
- Archived org blocks organization update
- Archived org blocks add member
- Archived org blocks brand create

### Packet 09 — done
- Archived org blocks member update/delete
- Archived org blocks brand update/delete

### Packet 10 — done
- Manager cannot promote to owner
- Manager cannot change owner role
- Manager cannot delete owner
- Owner can still promote to owner

### Packet 11 — done
- Manager cannot add a new member directly as `client_owner`
- Owner path for adding another owner preserved

### Packet 12 — done
- Owner downgrade policy hardened
- Last-owner role downgrade blocked

### Packet 13 — done
- Representative transition matrix behavior covered by regression tests
- Update-path policy gathered behind explicit transition helper

### Packet 14 — done
- Explicit create/update role matrices introduced
- Membership role policy normalized across create and update flows

### Packet 15 — done
- Explicit delete role matrix introduced
- Membership delete policy normalized behind dedicated helpers

### Packet 16 — done
- Organization membership role policy reference document
- Explicit create/update/delete role matrices documented
- ROADMAP is updated through Packet 16

### Packet 17 — done
- Organization status transitions split from ordinary metadata updates
- Manager can update name/slug but cannot change status
- Only owner can change organization status

### Packet 18 — done
- Archived organizations remain read-only for ordinary writes
- Owner can unarchive only through a status-only PATCH
- Manager cannot unarchive archived organizations

### Packet 19 — done
- Runtime config hardening: `DATABASE_URL` required, unsafe default JWT secret rejected in production/staging
- SQLite test artifacts moved out of repo tree and ignored

### Packet 20 — done
- Postgres-backed critical-path API lane added for auth/lifecycle/permission regressions
- Test DB backend selector introduced for SQLite vs Postgres harnessing
- Operator entrypoint added: `make api-test-postgres-critical-path`
- Verified remotely on Docker host: `19 passed`

### Packet 21 — done
- Brand-scoped `briefs` product baseline added: create/list/get
- Cross-organization `brand_id` vs `organization_id` mismatch is rejected with `409`
- Brief create path inherits archived-organization read-only enforcement
- Reviewer read path for briefs is live via list/get on accessible organizations
- Verified publicly on live API: create 201, list 200, get 200, mismatch 409

### Packet 22 — done
- Brand/brief-scoped `jobs` baseline added: create/list/get
- Job create requires manager/owner access on the organization
- Reviewer job read path is live via list/get on accessible organizations
- Job create validates `organization_id + brand_id + brief_id` linkage and rejects cross-org mismatches with `409`
- Archived organizations remain read-only for job creation
- Verified publicly on live API: create 201, list 200, get 200, mismatch 409

### Packet 23 — done
- Worker-only lifecycle hooks added: `claim`, `complete`, `fail`
- `jobs` now expose `started_at`, `finished_at`, and `error_message`
- Lifecycle transitions are guarded as `queued -> running -> completed/failed`
- Reviewer read path sees live execution state through existing job get/list endpoints
- `cf-worker` gained a minimal one-shot API hook client for lifecycle actions

### Packet 24 — done
- Worker-only `claim-next` queue selection added with oldest-queued semantics
- `jobs` now persist `worker_id` ownership
- Direct `claim` and `claim-next` stamp the owning worker
- `complete`/`fail` reject non-owning workers with `409`
- `cf-worker` gained one-shot `claim-next` support and now sends `X-Worker-Id`

### Packet 25 — done
- `jobs` now persist `lease_expires_at`
- `claim` and `claim-next` stamp a worker lease deadline
- Worker-only `heartbeat` endpoint extends the lease for the owning worker
- `claim-next` can reclaim stale running jobs before newer queued work
- `complete`/`fail` require both ownership and a live lease
- `cf-worker` gained one-shot `heartbeat` support

### Packet 26 — done
- `cf-worker` now runs a real polling loop in normal mode
- New worker tracer-bullet cycle: `claim-next -> heartbeat -> process -> complete/fail`
- Queue-empty `404` is treated as idle instead of crashing the worker
- Processing exceptions are translated into worker `fail` transitions
- Runtime observability emits `claimed`, `renewed lease`, `completed`, `failed`, and `idle` markers
- Dedicated worker tests cover the new loop behavior

### Packet 27 — done
- Worker now has an explicit `process_job()` contract
- Payload execution is modeled as a configurable multi-stage stub via `worker_process_stages`
- Lease renewal now happens across multiple processing stages
- Runtime observability emits stage markers for each processing step
- Stub output is deterministic from the job title, creating a stable seam for future payload/result packets
- Worker regression tests now cover both Packet 26 loop semantics and Packet 27 multi-stage processing semantics

### Packet 28 — done
- `jobs` now persist `attempt_count` as an execution marker that increments on each claim/reclaim
- `jobs` now persist `output_text` as the first durable worker result field
- Worker `complete` lifecycle now accepts an optional output payload
- `cf-worker` now forwards deterministic stub results into API completion instead of dropping them
- Public job read/list surfaces expose both `attempt_count` and `output_text`
- API and worker regression tests cover persisted output + reclaim-attempt semantics

### Packet 29 — done
- `jobs` now persist `last_stage` as the latest execution marker
- `jobs` now persist `last_heartbeat_at` as the latest lease-renew timestamp
- `claim` and `claim-next` now stamp `claimed` observability state immediately
- Worker heartbeats can now carry an optional `stage_name` payload
- `complete` and `fail` now stamp final stage markers (`completed` / `failed`)
- Public job read/list surfaces expose both observability fields
- API and worker regression tests cover stage-aware heartbeats and public readback semantics

### Packet 30 — done
- `jobs` now persist `output_artifact_key`, `output_artifact_url`, and `output_artifact_content_type`
- Worker `process_job()` now returns a deterministic artifact reference alongside stub text output
- Worker `complete` lifecycle now forwards optional artifact reference payloads into API completion
- Job claim/reclaim clears prior artifact reference fields so a new attempt starts cleanly
- Public job read/list surfaces expose artifact-reference fields
- API and worker regression tests cover artifact persistence and runtime propagation

### Packet 31 — done
- `cf-worker` now has S3/MinIO runtime config and a real object-storage helper
- Stub output is now uploaded as a real object during the `persist-artifact` stage when storage config is available
- Uploaded object refs are forwarded through the existing `complete` artifact payload seam into API persistence
- Legacy lightweight worker tests without storage config keep a deterministic fallback locator path
- Worker regression tests cover storage-write-backed artifact propagation

### Packet 32 — done
- `jobs` now persist `output_artifact_size_bytes` and `output_artifact_etag`
- Worker storage helper now performs `stat_object` after upload and returns size/etag metadata
- Worker `complete` payload forwards artifact metadata alongside existing locator fields
- API completion persists the artifact metadata and public job read/list surfaces expose it
- Job claim/reclaim clears prior artifact metadata fields so a new attempt starts cleanly
- API and worker regression tests cover metadata persistence and storage-stat propagation

### Packet 33 — done
- New authenticated `GET /api/v1/jobs/{job_id}/artifact` route
- Route reuses existing organization/job access control semantics
- API now has an object-storage read helper backed by MinIO/S3 settings
- Artifact readback returns stored bytes with the persisted artifact content type
- Jobs without a persisted artifact are rejected with `409 Job artifact is not available`
- API regression tests cover both successful text artifact readback and the no-artifact rejection path

### Packet 34 — done
- Worker artifact persistence now uses tenant-aware object keys: `organizations/{organization_id}/brands/{brand_id}/jobs/{job_id}/artifacts/result.txt`
- Worker runtime fallback paths also prefer the same namespaced key whenever job scope is available
- API artifact readback now validates that the persisted `output_artifact_key` exactly matches the expected job tenant namespace before reading object storage
- Readback rejects mismatched persisted keys with `409 Job artifact key is outside the job tenant namespace`
- Worker storage helper keeps backward-compatible fallback behavior for older narrow tests without full job scope
- API and worker regression tests cover both tenant-aware key generation and namespace enforcement on readback

### Packet 35 — done
- `JobRead` now exposes an explicit nested `scope` block with `organization_id`, `brand_id`, and `brief_id`
- Job list/get/claim/heartbeat/complete/fail readbacks all share the same explicit scope contract
- Worker runtime now validates that any completed artifact key exactly matches the expected tenant-aware namespace for the claimed job
- If an artifact key escapes job scope, worker fails the job with `processing error: artifact key escaped job scope` instead of completing it
- Scope enforcement is guarded so older narrow tests without full job scope remain compatible
- API and worker regression tests cover both explicit job scope readback and worker-side artifact-scope rejection

### Packet 36 — done
- `jobs` now persist `execution_trace_json` as a durable lifecycle trace envelope
- Public job read/list surfaces expose a structured `execution_trace` block with `scope`, `stage_history`, `artifact_scope_status`, `final_status`, and `failure_reason`
- Claim initializes a new trace from the job scope and stamps `claimed`
- Heartbeat appends stage history entries as the worker advances through processing stages
- Complete now validates `output_artifact_key` against the expected tenant-aware namespace before persisting completion
- Successful completion stamps `artifact_scope_status=validated` and final `completed` trace state
- Failure stamps final `failed` trace state and records `failure_reason`; artifact-scope failures are explicitly marked as `rejected`
- API regression tests cover both persisted trace readback and `409` rejection for out-of-scope completion artifact keys

### Packet 37 — done
- `execution_trace` now includes a structured `events` array alongside the existing backward-compatible summary fields
- Claim appends a `claimed` event with timestamp and `worker_id`
- Heartbeat appends `heartbeat` events with timestamp, `worker_id`, and `stage_name`
- Complete appends a `completed` event with timestamp, `worker_id`, and final `artifact_scope_status`
- Fail appends a `failed` event with timestamp, `worker_id`, `failure_reason`, and any artifact-scope rejection marker
- Existing `stage_history`, `artifact_scope_status`, `final_status`, and `failure_reason` remain intact for compatibility
- API regression tests now cover structured completed and failed event streams, and Packet 36 regression was updated for the expanded trace contract

### Packet 38 — done
- Terminal `completed` trace events now include an `artifact` snapshot with persisted `key`, `url`, `content_type`, `size_bytes`, and `etag`
- Terminal `completed` and `failed` trace events now include `stage_count`
- Terminal `completed` and `failed` trace events now include `lifecycle_seconds` measured from the initial `claimed` event timestamp
- Existing summary trace fields remain backward-compatible for consumers still reading `stage_history`, `artifact_scope_status`, `final_status`, and `failure_reason`
- API regression tests cover enriched completed and failed terminal trace details

### Packet 39 — done
- `execution_trace` now exposes `stage_timings` with `stage_name`, `entered_at`, `exited_at`, and `duration_seconds`
- Claim initializes the first `claimed` timing window, heartbeat stage transitions close/open stage windows, and terminal `completed` / `failed` windows are recorded explicitly
- Packet 38 terminal event details remain intact while stage-level timing moves into a dedicated timeline surface
- API regression tests cover both completed and failed stage timing traces

### Packet 40 — done
- Failed traces now include machine-readable `failure_stage` and `failure_code` at both top-level trace summary and failed terminal event level
- `failure_stage` is derived from the last non-terminal stage before transition into `failed`
- `failure_code` currently classifies `artifact_scope_rejection`, `upstream_timeout`, and falls back to `unknown_failure`
- API regression tests cover structured failed trace taxonomy without breaking Packet 38/39 trace surfaces

### Mini-batch 41–43 — done
- Heartbeat trace events now persist structured progress fields: `stage_label`, `progress_percent`, and `progress_message`
- Heartbeat trace events now persist machine-readable `worker_metadata`
- Claim and reclaim trace events now expose `claim_type` and `attempt_number`
- Reclaimed attempts also expose `reclaimed_from_worker_id` for stale-lease takeover visibility
- API regression tests cover structured heartbeat progress metadata and reclaimed-attempt trace details

### Mini-batch 44–46 — done
- `execution_trace` now exposes top-level `last_progress` with the latest structured heartbeat progress snapshot
- Reclaimed claims now classify `retry_reason=lease_expired` at both top-level trace summary and `claimed` trace events
- Terminal `completed` and `failed` events now carry forward `progress_context` from the latest heartbeat snapshot
- API regression tests cover last-progress snapshot persistence, terminal progress carry-forward, and retry-reason classification

### Mini-batch 47–49 — done
- Heartbeat events now carry `progress_sequence` and optional `transition_tag`
- `execution_trace.last_progress` now includes `attempt_number` and `progress_sequence`
- `execution_trace.progress_history` now stores the current attempt's ordered progress snapshots
- Reclaim resets progress history and restarts sequence numbering for the new attempt
- Terminal progress carry-forward now includes attempt-scoped progress metadata

### Mini-batch 50–52 — done
- Heartbeat events and attempt-scoped progress snapshots now carry `progress_delta_percent`
- `execution_trace` now exposes top-level `attempt_summary` for the current attempt
- Terminal `completed` and `failed` events now carry `attempt_snapshot`
- Reclaim resets `attempt_summary` alongside progress history for the new attempt
- API regression tests cover progress deltas, attempt summary shape, terminal attempt snapshot carry-forward, and reclaim reset semantics

### Mini-batch 53–55 — done
- `execution_trace.attempt_summary` now includes `attempt_duration_seconds`
- `execution_trace` now exposes top-level `stage_transition_counts`
- Terminal `completed` and `failed` events now carry `trace_summary`
- Reclaim resets transition counters and current-attempt duration context for the new attempt
- API regression tests cover attempt duration summary, stage transition counters, terminal trace summary carry-forward, and reclaim reset semantics

### Mini-batch 56–58 — done
- `execution_trace.attempt_summary` now includes `progress_velocity_percent_per_second`
- `execution_trace` now exposes top-level `dominant_stage_name`
- Terminal `completed` and `failed` events now carry `progress_digest`
- Reclaim resets dominant-stage focus and current-attempt velocity context for the new attempt
- API regression tests cover progress velocity summary, dominant stage selection, terminal progress digest carry-forward, and reclaim reset semantics

### Macro-chunk 59–68 — done
- `execution_trace.stage_duration_ranking` now ranks stages by total observed duration with transition counts and averages
- `execution_trace.attempt_summary` now includes `attempt_completion_ratio`, `last_stage_repeat_count`, and `attempt_event_density_per_second`
- `execution_trace.heartbeat_cadence_summary` now summarizes heartbeat count plus average/max inter-heartbeat gap
- `execution_trace.reclaim_continuity` now exposes current-attempt reclaim lineage
- `execution_trace.trace_compact_summary` now provides a compact current-stage/final-status/attempt snapshot
- Terminal `completed` and `failed` events now carry `timeline_digest` and `scope_recap`
- Terminal `failed` events now carry `failure_digest`
- API regression tests cover ranked timing, cadence, continuity, compact summaries, timeline digest, scope recap, and failure digest

### Macro-chunk 69–78 — done
- `execution_trace.progress_extrema` now exposes min/max/first progress plus span percent
- `execution_trace.retry_profile` now exposes attempt count, reclaim count, and latest attempt number
- `execution_trace.worker_history` now records current attempt worker lineage, including reclaim handoff
- `execution_trace.attempt_summary` now includes `progress_remaining_percent`, `first_progress_percent`, and `max_progress_percent`
- `execution_trace.trace_compact_summary` now includes `reclaim_count`
- Terminal `completed` and `failed` events now carry `worker_recap`
- Terminal `timeline_digest` now carries `progress_span_percent`
- Terminal `failed` events now carry `failure_digest.retry_reason`
- API regression tests cover extrema, retry profile, worker history, worker recap, progress span, remaining percent, first/max progress carry-forward, compact reclaim count, and failure retry context

### Macro-chunk 79–88 — done
- `execution_trace.transition_tag_rollup` now exposes ordered heartbeat transition tags for the current attempt
- `execution_trace.worker_metadata_key_summary` now exposes the sorted union of worker-metadata keys seen in progress heartbeats
- `execution_trace.stage_label_summary` now maps stage names to their latest human labels
- `execution_trace.attempt_summary` now includes `progress_sequence_span` and `total_progress_delta_percent`
- `execution_trace.retry_profile` now includes `current_claim_type`
- `execution_trace.trace_compact_summary` now includes `has_progress`
- Terminal `completed` and `failed` events now carry `progress_window`
- Terminal `timeline_digest` now carries `first_stage_name`
- Terminal `worker_recap` now carries `retry_reason`
- API regression tests cover transition rollups, metadata key summaries, stage-label summaries, progress sequence span, total progress delta, terminal progress window, first-stage digest, current claim type, compact has-progress, and worker retry context

### Macro-chunk 89–98 — done
- `execution_trace.transition_tag_counts` now exposes per-tag occurrence counts for the current attempt
- `execution_trace.latest_worker_metadata` now exposes the most recent worker metadata payload seen in progress heartbeats
- `execution_trace.stage_label_history` now preserves ordered label evolution per stage
- `execution_trace.attempt_summary` now includes `last_stage_label` and `average_progress_delta_percent`
- `execution_trace.trace_compact_summary` now includes `progress_span_percent`
- Terminal `timeline_digest` now carries `last_progress_sequence`
- Terminal `progress_digest` now carries `total_progress_delta_percent`
- Terminal `worker_recap` now carries `current_claim_type`
- Terminal `failure_digest` now carries `progress_remaining_percent`
- API regression tests cover transition-tag counts, latest worker metadata snapshots, stage-label history, average progress delta, last-stage label carry-forward, compact progress span, timeline last sequence, failure remaining percent, worker claim-type recap, and progress total delta digests

### Macro-chunk 99–108 — done
- `execution_trace.unique_transition_tag_count` now exposes the count of distinct transition tags seen in the current attempt
- `execution_trace.progress_history_sample_count` now exposes the number of progress samples captured in the current attempt
- `execution_trace.attempt_summary` now includes `average_progress_percent`
- `execution_trace.trace_compact_summary` now includes `last_stage_label`
- Terminal `timeline_digest` now carries `first_progress_percent`
- Terminal `progress_digest` now carries `average_progress_delta_percent`
- Terminal `progress_window` now carries `progress_sequence_span`
- Terminal `failure_digest` now carries `current_claim_type`
- Terminal `worker_recap` now carries `had_reclaim`
- API regression tests cover unique transition counts, progress sample counts, average progress percent, compact last-stage labels, timeline first-progress carry-forward, average progress delta digests, progress-window sequence spans, failure claim-type carry-forward, and reclaim markers in worker recap

### Macro-chunk 109–118 — done
- `execution_trace.attempt_summary` now includes `min_progress_percent` and `unique_stage_count`
- `execution_trace.trace_compact_summary` now includes `average_progress_percent` and `unique_transition_tag_count`
- Terminal `timeline_digest` now carries `first_progress_sequence` and `latest_stage_label`
- Terminal `progress_digest` now carries `average_progress_percent`
- Terminal `progress_window` now carries `min_progress_percent`
- Terminal `failure_digest` now carries `had_reclaim`
- Terminal `worker_recap` now carries `reclaim_count`
- API regression tests cover min progress carry-forward, unique stage counts, compact average/count summaries, timeline first-sequence and latest-label recaps, progress average digests, progress-window min-progress carry-forward, failure reclaim flagging, and worker reclaim counters

### Macro-chunk 119–128 — done
- `execution_trace.attempt_summary` now includes `unique_transition_tag_count`
- `execution_trace.trace_compact_summary` now includes `progress_history_sample_count`, `unique_stage_count`, and `worker_count`
- Terminal `timeline_digest` now carries `first_stage_label` and `latest_progress_percent`
- Terminal `progress_digest` now carries `min_progress_percent` and `progress_remaining_percent`
- Terminal `progress_window` now carries `average_progress_percent`
- Terminal `failure_digest` now carries `reclaim_count` and `worker_count`
- Terminal `worker_recap` now carries `attempt_count`
- API regression tests cover attempt tag-count carry-forward, compact progress sample/stage/worker counts, timeline first-stage labels and latest progress percent, progress digest floor/remaining carry-forward, progress-window average progress, failure reclaim/worker totals, and worker attempt totals

### Macro-chunk 129–138 — done
- `execution_trace.attempt_summary` now includes `first_stage_label` and `latest_transition_tag`
- `execution_trace.trace_compact_summary` now includes `latest_transition_tag`, `worker_metadata_key_count`, and `stage_label_entry_count`
- Terminal `timeline_digest` now carries `latest_transition_tag`
- Terminal `progress_digest` now carries `max_progress_percent` and `unique_transition_tag_count`
- Terminal `progress_window` now carries `total_progress_delta_percent`
- Terminal `failure_digest` now carries `latest_transition_tag`
- Terminal `worker_recap` now carries `latest_transition_tag`
- API regression tests cover first-stage-label and latest-tag carry-forward, compact metadata/label counters, timeline latest transition tags, progress-digest max/tag recaps, progress-window total-delta carry-forward, and failure/worker latest-tag context

### Macro-chunk 139–148 — done
- `execution_trace.attempt_summary` now includes `first_transition_tag` and `worker_metadata_key_count`
- `execution_trace.trace_compact_summary` now includes `transition_tag_total_count` and `latest_worker_metadata_keys`
- Terminal `timeline_digest` now carries `first_transition_tag` and `latest_worker_metadata_keys`
- Terminal `progress_digest` now carries `first_progress_percent`
- Terminal `progress_window` now carries `progress_span_percent`
- Terminal `failure_digest` now carries `attempt_completion_ratio`
- Terminal `worker_recap` now carries `latest_worker_metadata_keys`
- API regression tests cover first-tag carry-forward, attempt metadata breadth counts, compact total-tag and latest-metadata-key summaries, timeline first-tag/latest-metadata-key recaps, progress-digest first-progress carry-forward, progress-window spread carry-forward, failure completion-ratio carry-forward, and worker latest-metadata-key context

### MVP Track 01–08 — done
- Roadmap focus is explicitly shifted from deeper execution-trace enrichment to MVP-first web delivery
- Further additive trace-contract expansion is now treated as post-MVP work unless it blocks the product flow
- API now serves browser-safe CORS preflight for the real app origin `https://app.uno-ai.pw`
- `apps/web` is no longer a stub: `/` redirects based on session state, `/login` performs live auth, and `/dashboard` reads the real authenticated profile via `/api/v1/auth/me`
- The web shell stores a minimal local browser session and now persists the selected organization/brand scope for upcoming brief/job screens
- Dashboard now reads real organizations from `/api/v1/organizations`, real brands from `/api/v1/brands?organization_id=...`, real briefs from `/api/v1/briefs`, and real jobs from `/api/v1/jobs`
- Dashboard can now create a brief in the selected scope, create a job from the selected brief, render the resulting live job list, and load selected job detail/status via `/api/v1/jobs/{job_id}`
- Dashboard now exposes `output_text`, authenticated artifact download, textual artifact preview, and persisted artifact metadata directly in the selected job panel
- Reviewer scope is now explicitly read-only in the dashboard: create-brief/create-job affordances are replaced with explanatory notices, while manager/owner retain write forms
- Brand deletion is now explicitly split by data shape: empty brands remain hard-deletable, while brands that already carry briefs/jobs return `409` instead of cascading destructive deletes
- Public `cf-web` now runs in production mode (`next start`) instead of a dev/HMR runtime
- Public `cf-api` now runs as a plain production `uvicorn` process without `--reload`/watchfiles reloader semantics
- Verification now includes web production-readiness build checks, full API regression, live API artifact readback, live browser-context create/list/detail/result/artifact checks against the public app/API, and public empty-vs-populated brand delete proof

### Post-MVP Phase 01 / Internal Roles Packet 01 — done
- Canonical internal executor role registry now exists for `mike`, `emma`, `iris`, `sarah`, `adrian`, `alex`, `david`, `bob`
- Initial execution profiles are defined and resolved at job creation time
- Job create/get/list APIs now expose additive internal execution metadata through `execution_profile` and ordered `internal_role_plan`
- Live Postgres schema is upgraded through Alembic revision `20260704_013`
- Public API proof confirms live `seo_content` readback with ordered internal role plan

### Post-MVP Phase 01 / Internal Roles Packet 02 — done
- Worker execution is now role-aware for jobs carrying `internal_role_plan`, while legacy jobs still fall back to generic worker stages
- Live role-aware traces now preserve the full ordered internal role chain from `role:mike` through `role:david`
- Worker heartbeats now persist role labels, progress, transition tags, and per-role worker metadata into the existing trace contract
- Public live worker/API proof confirms the canonical `seo_content` role chain in `execution_trace.stage_history`

### Post-MVP Phase 01 / Internal Roles Packet 03 — done
- Public dashboard job detail now shows `execution_profile` and ordered `internal_role_plan`
- The UI renders each internal role with sequence number, label, role id, and purpose
- Public live browser proof confirms the Packet95 role-aware job now exposes the internal execution plan in the shipped UI
- Web production build and full API regression remain green after the dashboard exposure change
### Organization Lifecycle Packet 17 — done
Goal completed: extend the paused-organization lifecycle coverage to content version promotion so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet194.py` covers paused-organization content version promotion blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 16 — done
Goal completed: extend the paused-organization lifecycle coverage to content item review actions so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet193.py` covers paused-organization content item review blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 15 — done
Goal completed: extend the paused-organization lifecycle coverage to product DNA generation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet192.py` covers paused-organization product DNA generation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 14 — done
Goal completed: extend the paused-organization lifecycle coverage to brand DNA generation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet191.py` covers paused-organization brand DNA generation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 13 — done
Goal completed: extend the paused-organization lifecycle coverage to content item generation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet190.py` covers paused-organization content item generation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 12 — done
Goal completed: extend the paused-organization lifecycle coverage to ticket creation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet189.py` covers paused-organization ticket creation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 11 — done
Goal completed: extend the paused-organization lifecycle coverage to content version creation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet188.py` covers paused-organization content version creation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 10 — done
Goal completed: extend the paused-organization lifecycle coverage to content plan creation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet187.py` covers paused-organization content plan creation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 09 — done
Goal completed: extend the paused-organization lifecycle coverage to audience segment creation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet186.py` covers paused-organization audience segment creation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Organization Lifecycle Packet 08 — done
Goal completed: extend the paused-organization lifecycle coverage to media asset creation so the same read-only contract is enforced across another reachable content-write route.

Delivered scope:
- `apps/api/tests/test_packet185.py` covers paused-organization media asset creation blocking
- `docs/organization-lifecycle-policy.md` now lists the new regression coverage entry

### Post-MVP Phase 01 / Internal Roles Packet 07 — done
Goal completed: add sensitive permission-change audit logging plus an owner/manager readback surface for recovery and support workflows.

Delivered scope:
- `apps/api/app/api/v1/organizations.py` now records audit events for membership create/update/delete and organization status changes
- `apps/api/app/api/v1/organizations.py` now exposes `GET /api/v1/organizations/{organization_id}/permission-events` for manager/owner readback
- `apps/api/app/db/models/organization_permission_event.py` stores the permission audit trail
- `apps/api/tests/test_packet184.py` covers persistence, readback, and documentation coverage

### Post-MVP Phase 01 / Internal Roles Packet 06 — done
Goal completed: expose an execution-profile selector in the job creation form so operators can choose the supported internal role chain at creation time.

Delivered scope:
- `apps/web/app/dashboard/page.tsx` now exposes an execution profile selector in the job creation form and submits the chosen profile with `createJob`
- `apps/web/lib/api.ts` now allows the job-create payload to carry an optional `execution_profile`
- `apps/api/tests/test_packet183.py` covers the new selector contract and the expanded API client signature
- Web production build and full API regression remain green after the selector change

## Next roadmap
### Immediate next product work
1. Operator and admin workflows for recovery / support scenarios
2. Add stricter lifecycle semantics for org- and brand-level states
3. Decide whether paused should have narrower write semantics than active
4. Expand the Postgres-backed critical-path lane into broader API integration coverage and CI/runtime automation
5. Continue public-facing documentation sync for any new operator workflows

## Why this roadmap matters
The work completed so far is not isolated CRUD. It creates the production-safe foundation required for every later feature:
- multi-tenant org boundaries
- safe collaboration across members
- role-based permission enforcement
- archived/read-only lifecycle behavior
- production deployment that can be tested publicly after every slice

Without this layer, later workflow/content features would sit on unstable authorization and lifecycle rules. With it, the next product layers can build on a predictable platform.
