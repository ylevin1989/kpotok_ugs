# Scope model

This document defines the reusable content scope contract that future generation endpoints will use.

## Scope values
- `brand`
- `product`
- `campaign`
- `comparison`

## Rule
- `scope=product` requires `product_id`
- the other scopes do not require a product reference

## Source of truth
- `apps/api/app/domain/content_scope.py`
- `apps/api/app/schemas/scope.py`
