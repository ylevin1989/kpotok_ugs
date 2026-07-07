# Content Factory

Content Factory is a control plane and application layer built on top of an existing Hermes runtime.

## Services
- cf-web
- cf-api
- cf-worker
- cf-postgres
- cf-redis
- cf-minio

## Internal execution roles
See [`docs/internal-roles.md`](docs/internal-roles.md) for the canonical role registry, execution profiles, and role-specific prompting behavior.

## Internal execution API bundle
See [`docs/internal-execution-api-bundle.md`](docs/internal-execution-api-bundle.md) for the client-facing summary of `execution_profile` and `internal_role_plan`.

## Jobs API reference
See [`docs/jobs-api-reference.md`](docs/jobs-api-reference.md) for request/response examples for `execution_profile` and `internal_role_plan`.

## Organization lifecycle policy
See [`docs/organization-lifecycle-policy.md`](docs/organization-lifecycle-policy.md) for active/paused/archived organization behavior.

## Brand lifecycle policy
See [`docs/brand-lifecycle-policy.md`](docs/brand-lifecycle-policy.md) for active/paused/archived brand behavior.

## Operator support and recovery
See [`docs/operator-support-recovery.md`](docs/operator-support-recovery.md) for the platform-admin lookup workflow.

## Scope model
See [`docs/scope-model.md`](docs/scope-model.md) for the reusable content scope contract and `scope=product` validation rule.

## Media assets
See [`docs/media-assets.md`](docs/media-assets.md) for the current media asset metadata surface and validation rules.

## Audience segments
See [`docs/audience-segments.md`](docs/audience-segments.md) for the current audience-segment metadata surface and validation rules.

## Content plans
See [`docs/content-plans.md`](docs/content-plans.md) for the planning surface, scope rules, and API shape.

## Content items
See [`docs/content-items.md`](docs/content-items.md) for the execution-ready item surface, quality score, and API shape.

## Content versions
See [`docs/content-versions.md`](docs/content-versions.md) for append-only versioning, current-version rules, and API shape.

## Quality checks
See [`docs/quality-checks.md`](docs/quality-checks.md) for QA records, version defaulting, score mirroring, and gating into client review or `internal_review`.

## Local run
```bash
cp .env.example .env
docker compose up --build
```
