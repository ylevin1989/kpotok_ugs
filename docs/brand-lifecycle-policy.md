# Brand lifecycle policy

## Purpose
This document is the human-readable reference for the current brand lifecycle policy implemented in `apps/api/app/api/v1/brands.py` and the content write guards that depend on it.

## Status model
- `active`
- `paused`
- `archived`

## Current behavior
### Active brands
- Normal write behavior.
- Brand metadata updates and content writes are allowed for permitted managers/owners.

### Paused brands
- Brand metadata updates are still allowed where the route already permits them.
- Content write endpoints are read-only for paused brands.
- Error detail for blocked content writes: `Paused brand is read-only for content writes`

### Archived brands
- Ordinary brand and content write paths remain read-only.
- Error detail for blocked archived writes:
  - `Archived brand is read-only`
  - `Archived brand is read-only for content writes`

## Current implementation source of truth
- `apps/api/app/api/v1/brands.py`
- `apps/api/app/api/v1/brand_lifecycle.py`
- `apps/api/app/api/v1/products.py`
- `apps/api/app/api/v1/briefs.py`
- `apps/api/app/api/v1/content_plans.py`
- `apps/api/app/api/v1/content_items.py`
- `apps/api/app/api/v1/content_versions.py`
- `apps/api/app/api/v1/media_assets.py`
- `apps/api/app/api/v1/audience_segments.py`
- `apps/api/app/api/v1/quality_checks.py`
- `apps/api/app/api/v1/jobs.py`

## Current regression coverage
- `apps/api/tests/test_packet201.py`
- `apps/api/tests/test_packet202.py`
- `apps/api/tests/test_packet203.py`
