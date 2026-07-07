# Operator support and recovery workflow

## Purpose
This document is the human-readable reference for the operator support lookup workflow exposed to platform admins.

## Current flow
- Platform admins can search a user by email.
- The lookup returns the user record plus accessible organization memberships.
- Non-admin users are blocked from this workflow.

## API surface
- `GET /api/v1/support/users?email=...`
- Access gate: `require_platform_admin()`

## UI surface
- `apps/web/app/support/page.tsx`
- Dashboard entry point for platform admins in `apps/web/app/dashboard/page.tsx`

## Current implementation source of truth
- `apps/api/app/api/v1/support.py`
- `apps/api/app/api/deps.py`
- `apps/api/app/schemas/support.py`
- `apps/web/lib/api.ts`
- `apps/web/lib/types.ts`
- `apps/web/app/support/page.tsx`
- `apps/web/app/dashboard/page.tsx`

## Current regression coverage
- `apps/api/tests/test_packet200.py`
