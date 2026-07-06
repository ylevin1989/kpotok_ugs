# SEO content role-run example

This is a worked example of the `seo_content` execution profile in the current Content Factory worker pipeline.

## Execution order
1. Mike
2. Emma
3. Iris
4. Sarah
5. Alex
6. David

## What each role contributes

### Mike
- Confirms execution order
- Frames the routing logic
- Flags any dependency or sequencing risk

### Emma
- Checks the work against the product goal
- Protects the desired outcome
- Removes direction that weakens the product meaning

### Iris
- Adds market context
- Summarizes ICP and pains
- Surfaces useful research signals

### Sarah
- Identifies organic search angles
- Frames keyword intent
- Proposes SEO topic structure

### Alex
- Turns prior inputs into a usable draft or brief
- Structures the content so it can be shipped
- Hands off a concrete artifact

### David
- Checks for inconsistencies and gaps
- Calls out efficiency issues
- Verifies the chain is coherent before output compilation

## Example compiled flow
- Mike: route `seo_content` through the SEO branch
- Emma: confirm the output should satisfy a search-driven product use case
- Iris: provide market and audience context for the target topic
- Sarah: turn that context into search-intent and keyword framing
- Alex: assemble the brief into a draft content artifact
- David: review the chain for consistency and output quality

## Source of truth
- `apps/api/app/domain/internal_agent_roles.py`
- `apps/worker/app/role_prompts.py`
- `apps/worker/app/llm_client.py`
- `docs/internal-roles.md`
- `docs/jobs-api-reference.md`
