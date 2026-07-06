# Current task

## Task ID
phase_50_product_ui_shell_stage2

## Status
Completed.

## What shipped
- `apps/web/lib/types.ts` now includes `ContentScope`, `MediaAsset*`, and `AudienceSegment*` browser contracts
- `apps/web/lib/api.ts` now includes `getMediaAssets`, `createMediaAsset`, `getAudienceSegments`, and `createAudienceSegment`
- `apps/web/app/media-assets/page.tsx` introduces a media library workspace with org/brand/product scope selection and asset creation
- `apps/web/app/audience-segments/page.tsx` introduces an audience segment workspace with org/brand/product scope selection and segment creation
- `apps/web/app/dashboard/page.tsx` links to `/media-assets` and `/audience-segments` in addition to brands/products

## Verification
- `npm run build` in `apps/web` succeeds

## Next packet
Proceed to stage3-plan-generation: implement end-to-end content-plan generation from scope, dates, and Brand/Product DNA context
