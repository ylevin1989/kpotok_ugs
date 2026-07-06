# Billing and usage

## Scope
This document covers the monetization and usage accounting layer for content-plan export and generation.

## Current API surface
- `GET /api/v1/subscriptions?organization_id=...`
- `POST /api/v1/subscriptions`
- `GET /api/v1/subscriptions/usage?organization_id=...`
- `POST /api/v1/content-plans/export`
- `POST /api/v1/content-plans/generate`

## Behavior
- Each organization has a subscription record with monthly limits for content-plan generation and export.
- Generation records usage by the number of generated plans in the requested date range.
- Export records usage per export request.
- Requests are blocked when the monthly limit would be exceeded.
- Inactive subscriptions are blocked from generation and export.

## UI
- `/subscriptions` lets managers inspect and edit the current organization subscription.
- `/content-plans` provides export support and links to the subscription workspace.
