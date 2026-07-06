# Current task

## Task ID
phase_49_product_ui_shell_stage1

## Status
Completed.

## What shipped
- `apps/web/lib/types.ts` now includes product domain types for the browser client
- `apps/web/lib/api.ts` now includes product API helpers for list/create/update/generate-dna
- `apps/web/app/products/page.tsx` introduces a dedicated product workspace with list, create/edit form, and Product DNA job trigger
- `apps/web/app/dashboard/page.tsx` links to the new products workspace
- `.gitignore` now ignores `.hermes/` and backup artifacts, and the repository is initialized with git

## Verification
- `npm run build` in `apps/web` succeeds

## Next packet
Continue with the next product-facing UI slice: brand page, media library, audience segments, or the next dependency needed by the product workspace
