# Products contract

This document describes the current product-domain contract implemented in the API.

## Route surface

- `GET /api/v1/products?organization_id=&brand_id=`
- `POST /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `PATCH /api/v1/products/{product_id}`
- `POST /api/v1/products/{product_id}/generate-dna`

## Scope rules

Products are always scoped by:
- `organization_id`
- `brand_id`

The API rejects products that do not belong to the requested organization/brand combination.

## Create and update fields

A product carries these user-facing fields:
- `sku`
- `name`
- `category`
- `description`
- `features`
- `benefits`
- `proofs`
- `objections`
- `restrictions`
- `status`
- `readiness_score`

The `organization_id` and `brand_id` are immutable once the record exists.

## DNA generation

`POST /api/v1/products/{product_id}/generate-dna` creates a brief/job pair for product DNA generation.
The resulting DNA snapshot is stored back onto the product record when the job completes.

## Lifecycle guard

Product writes reuse the shared content-write guard:
- paused organizations are read-only for product writes
- archived organizations are also read-only for product writes

## Validation

- `sku` must remain unique within the organization/brand scope
- `readiness_score` stays within `0..100`
