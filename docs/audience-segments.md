# Audience segments

This document covers the current audience-segment metadata surface.

## Purpose
Audience segments capture reusable audience/persona context for brand- and product-scoped content work.

## Current contract
- `organization_id`
- `brand_id`
- `product_id` when `scope=product`
- `scope`: `brand`, `product`, `campaign`, `comparison`
- `name`
- `description`
- `pain_points`
- `goals`
- `objections`
- `keywords`

## Validation rules
- `scope=product` requires `product_id`
- product-scoped segments must belong to the same organization and brand as the segment record
- segment names are unique within `organization_id + brand_id`

## Source of truth
- `apps/api/app/db/models/audience_segment.py`
- `apps/api/app/api/v1/audience_segments.py`
- `apps/api/app/schemas/audience_segment.py`
- `apps/api/tests/test_packet163.py`
