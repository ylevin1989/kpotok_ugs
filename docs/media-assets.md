# Media assets

This document covers the current media asset metadata surface.

## Purpose
Media assets store reusable brand/product visuals and content files as metadata records scoped by organization and brand, with optional product attachment.

## Current contract
- `organization_id`
- `brand_id`
- `product_id` when `scope=product`
- `scope`: `brand`, `product`, `campaign`, `comparison`
- `name`
- `description`
- `asset_key`
- `source_url`
- `content_type`
- `size_bytes`
- `checksum`

## Validation rules
- `scope=product` requires `product_id`
- product-attached assets must belong to the same organization and brand as the asset record
- asset keys are unique within `organization_id + brand_id`

## Source of truth
- `apps/api/app/db/models/media_asset.py`
- `apps/api/app/api/v1/media_assets.py`
- `apps/api/app/schemas/media_asset.py`
- `apps/api/tests/test_packet162.py`
