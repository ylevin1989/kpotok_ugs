# Current task

## Task ID
web-production-flow-packet-01

## Status
Completed.

## What shipped
- Added `/production-flow` as a guided client-side coordinator for the existing product workspaces.
- The new page shows the current organization/brand scope, counts for products/segments/briefs/plans/jobs, and the next recommended action.
- Dashboard and onboarding now link to the production flow as the primary entrypoint.
- The production flow reuses the established domain screens for the actual writes instead of introducing a separate workflow backend.
- Added in-page quick actions for creating a brief and generating content plans from the current scope.

## Verification
- `npm run build` in `apps/web`
- `docker compose build cf-web`
- `docker compose up -d --force-recreate cf-web`
- Live browser smoke on `https://app.uno-ai.pw/production-flow` after login

## Next packet
- Wait for the next user-directed step after deploy / live verification if requested.
