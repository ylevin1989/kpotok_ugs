# Organization permission audit log

## Purpose
This document is the human-readable reference for the current audit trail that records sensitive organization permission changes.

## Logged events
The API records audit events for:
- `membership_created`
- `membership_role_changed`
- `membership_deleted`
- `organization_status_changed`

Each event stores:
- organization id
- actor user id
- actor membership role
- action
- target type and target id
- optional structured details JSON
- created timestamp

## Readback surface
Managers and owners can inspect the audit trail through:
- `GET /api/v1/organizations/{organization_id}/permission-events`

## Current implementation source of truth
- `apps/api/app/api/v1/organizations.py`
- `apps/api/app/db/models/organization_permission_event.py`
- `apps/api/app/schemas/organization.py`

## Current regression coverage
- `apps/api/tests/test_packet184.py`
