# Organization lifecycle policy

## Purpose
This document is the human-readable reference for the current organization lifecycle policy implemented in `apps/api/app/api/v1/organizations.py` and the content write guards that depend on it.

## Status model
- `active`
- `paused`
- `archived`

## Current behavior
### Active organizations
- Normal write behavior.
- Content creation and content updates are allowed for permitted managers/owners.

### Paused organizations
- Owner/manager status changes are still allowed where the route already permits them.
- Content write endpoints are read-only for paused organizations.
- Job creation is also read-only for paused organizations.
- Error detail for blocked content writes: `Paused organization is read-only for content writes`

### Archived organizations
- Ordinary content/member/brand write paths remain read-only.
- Exception: an owner may send a status-only PATCH to move an organization out of `archived`.
- Error detail for blocked archived writes: `Archived organization is read-only`

## Current implementation source of truth
- `apps/api/app/api/v1/organizations.py`
- `apps/api/app/api/v1/briefs.py`
- `apps/api/app/api/v1/brands.py`
- `apps/api/app/api/v1/content_plans.py`
- `apps/api/app/api/v1/content_items.py`
- `apps/api/app/api/v1/content_versions.py`
- `apps/api/app/api/v1/media_assets.py`
- `apps/api/app/api/v1/audience_segments.py`
- `apps/api/app/api/v1/quality_checks.py`
- `apps/api/app/api/v1/tickets.py`
- `apps/api/app/api/v1/jobs.py`
- `apps/api/app/api/v1/products.py`

## Current regression coverage
- `apps/api/tests/test_packet17.py`
- `apps/api/tests/test_packet171.py`
- `apps/api/tests/test_packet172.py`
- `apps/api/tests/test_packet173.py`
- `apps/api/tests/test_packet174.py`
- `apps/api/tests/test_packet175.py`
- `apps/api/tests/test_packet185.py`
- `apps/api/tests/test_packet186.py`
- `apps/api/tests/test_packet187.py`
- `apps/api/tests/test_packet188.py`
- `apps/api/tests/test_packet189.py`
- `apps/api/tests/test_packet190.py`
- `apps/api/tests/test_packet191.py`
- `apps/api/tests/test_packet192.py`
- `apps/api/tests/test_packet193.py`
- `apps/api/tests/test_packet194.py`
