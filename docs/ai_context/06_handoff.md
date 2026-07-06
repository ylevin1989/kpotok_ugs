# Handoff

## Summary for the next packet
- The product-facing UI shell is live at `/products`.
- Dashboard now links into the product workspace.
- The repo is now under git, with backups and `.hermes/` ignored.
- Next work should expand adjacent product UI slices, not re-open the API update packet.

## Do next
- Add the brand screen or another product-adjacent UI slice that the product workspace depends on.
- Keep the products workspace and dashboard scope selection consistent.
- Reuse the existing auth/session storage and product API helpers.

## Do not do
- Do not expand jobs/admin yet.
- Do not remove the current product list/edit flow.
- Do not change the existing API product contract unless the next slice requires it.
