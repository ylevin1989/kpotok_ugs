# Handoff

## Summary for the next packet
- The new `/production-flow` page is now the guided entrypoint for the live product workspaces.
- It shows current org/brand scope, counts for products/segments/briefs/plans/jobs, and a recommended next action.
- Dashboard and onboarding now link into the flow so users can start from one obvious place.
- The actual create/edit actions still live in the dedicated domain screens, which keeps the coordinator thin and avoids duplicate workflow state.
- The coordinator now also offers in-page quick actions for creating a brief and generating content plans from the current scope.
- The visible UI copy on the main product pages is now Russian-only.
- The Russian-first cleanup now also covers subscriptions, media assets, products, content plans, audience segments, support, dashboard, and the production-flow coordinator.

## Do next
- Continue with the next user-directed packet only after deploy / live verification if requested.
- If the user wants a deeper workflow upgrade, extend the coordinator with richer recommendations rather than reintroducing a second write surface.

## Do not do
- Do not fall back to a separate workflow backend unless the product explicitly needs it.
- Do not duplicate the existing create/edit forms inside the coordinator page.
