# Internal execution roles

This document describes the canonical internal execution roles and execution profiles used by Content Factory.

## Source of truth
- `apps/api/app/domain/internal_agent_roles.py`
- `apps/api/app/schemas/job.py`
- `apps/worker/app/llm_client.py`
- `apps/worker/app/role_prompts.py`

## Roles

| role_id | label | purpose |
|---|---|---|
| mike | Mike | Internal production manager who routes tasks and frames execution order. |
| emma | Emma | Product manager who protects product meaning and desired outcome. |
| iris | Iris | Researcher who derives market, ICP, pains, and trend inputs. |
| sarah | Sarah | SEO specialist who shapes organic search angles and keyword intent. |
| adrian | Adrian | Ads specialist who shapes offers, hooks, and paid acquisition angles. |
| alex | Alex | Content constructor who assembles drafts, scripts, and visual/content briefs. |
| david | David | Data analyst who reviews consistency, deviations, and efficiency signals. |
| bob | Bob | Architect who handles process/system issues and integration thinking. |

## Execution profiles

| execution_profile | ordered roles |
|---|---|
| general_content | mike → emma → iris → alex → david |
| seo_content | mike → emma → iris → sarah → alex → david |
| ads_content | mike → emma → iris → adrian → alex → david |
| architecture_support | mike → bob → david |

## Prompting behavior

Each role receives:
1. a shared system prompt that keeps the output concise and compilable;
2. a role-specific focus line derived from the role id;
3. the job title, execution profile, role label, role purpose, stage name, and prior role outputs.

The worker then compiles all role outputs into the final job artifact and preserves the ordered role chain in the job trace.
