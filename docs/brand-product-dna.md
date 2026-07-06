# Brand/Product DNA

This document describes the current DNA generation contract for brands and products.

## Current contract

### Brand DNA
- `POST /api/v1/brands/{brand_id}/generate-dna`
- Creates a queued job for the selected brand
- When the job completes, the generated JSON is stored on `brands.dna_json`

### Product DNA
- `POST /api/v1/products/{product_id}/generate-dna`
- Creates a queued job for the selected product
- When the job completes, the generated JSON is stored on `products.dna_json`

## Persisted shape

The stored value is a JSON object with metadata and the generated DNA payload:

```json
{
  "kind": "brand_dna_generation",
  "source_job_id": "...",
  "source_brief_id": "...",
  "dna": {
    "positioning": "...",
    "tone_of_voice": "..."
  }
}
```

For product DNA, `kind` is `product_dna_generation` and the payload can include product summary, features, benefits, proofs, objections, and content angles.

## Notes

- The DNA generation flow uses the existing `brief → job → worker → complete` pipeline.
- The worker output must be valid JSON text so the API can persist it into the target record.
- The brand and product records remain the source of truth for their current DNA snapshot.
