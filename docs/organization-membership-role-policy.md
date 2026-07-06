# Organization membership role policy

## Purpose
This document is the human-readable reference for the current organization membership authorization model implemented in `apps/api/app/api/v1/organizations.py`.

It exists so that role behavior is not hidden only inside route helpers and tests. It documents the current production policy for create, update, and delete membership operations.

## Role model
- `owner`
- `manager`
- `reviewer`

In API payloads and DB enums these map to:
- `client_owner`
- `client_manager`
- `client_reviewer`

## Create matrix
Actor role -> roles that actor may assign when adding a new member.

| actor | allowed assigned roles |
|---|---|
| owner | owner, manager, reviewer |
| manager | manager, reviewer |

## Update matrix
Actor role + target current role -> roles that actor may set.

| actor | target current role | allowed target roles |
|---|---|---|
| owner | owner | owner, manager, reviewer |
| owner | manager | owner, manager, reviewer |
| owner | reviewer | owner, manager, reviewer |
| manager | manager | manager, reviewer |
| manager | reviewer | manager, reviewer |

## Delete matrix
Actor role -> target roles that actor may delete.

| actor | allowed target roles |
|---|---|
| owner | owner, manager, reviewer |
| manager | manager, reviewer |

## Cross-cutting invariants
These rules apply on top of the raw matrices.

1. Archived organizations are read-only for ordinary organization/member/brand write paths.
   - Exception: an owner may send a status-only PATCH to move an organization out of `archived`.
   - Error detail for blocked archived writes: `Archived organization is read-only`
2. Only owners can assign the owner role.
   - Error detail: `Only owners can assign owner role`
3. Only owners can modify owner memberships.
   - Error detail: `Only owners can modify owner memberships`
4. Owner role downgrade cannot remove the final owner role from an organization.
   - Error detail: `Cannot change the last owner role`
5. A user cannot delete their own membership.
   - Error detail: `Cannot remove your own membership`
6. Owner deletion cannot remove the final remaining owner.
   - Error detail: `Cannot remove the last owner`
7. Sensitive permission changes are audit logged and can be read back through the organization permission-events endpoint.

## Interpretation notes
- The matrices define the baseline allow-list.
- The invariants above are stronger rules and take precedence over a matrix allow-list.
- In practice this means a matrix may say an owner can touch owner memberships, but the last-owner safeguards still block destructive terminal cases.
- Delete policy is intentionally modeled separately from update policy because self-delete and last-owner delete safeguards are operation-specific.

## Current implementation source of truth
Current implementation lives in:
- `apps/api/app/api/v1/organizations.py`
- `docs/organization-permission-audit-log.md`

Current regression coverage lives in:
- `apps/api/tests/test_packet10.py`
- `apps/api/tests/test_packet12.py`
- `apps/api/tests/test_packet13.py`
- `apps/api/tests/test_packet14.py`
- `apps/api/tests/test_packet15.py`
- `apps/api/tests/test_packet16.py`
- `apps/api/tests/test_packet184.py`
