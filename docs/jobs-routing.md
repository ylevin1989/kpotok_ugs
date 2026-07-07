# Jobs routing contract

## Goal
Make job completion routing explicit and stable.

## Job kinds
- `content_generation`
- `dna_generation`
- `ticket_processing`
- `manual` for legacy/generic jobs

## Typed target references
Jobs now carry explicit target ids instead of inferring them from brief JSON:
- `target_brand_id`
- `target_product_id`
- `target_content_item_id`
- `target_ticket_id`

## Current behavior
- Job creation endpoints set `job.kind` and typed targets directly.
- Job completion uses `job.kind` first.
- Legacy brief JSON parsing is preserved only as a fallback for old `manual` jobs.

## Why this matters
- Routing no longer breaks when brief payload shape changes.
- Completion logic is now inspectable from the job row itself.
- Backfill remains possible for historical jobs.
