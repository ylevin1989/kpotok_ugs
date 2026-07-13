from __future__ import annotations

from typing import Any

COMMON_SYSTEM_PROMPT = (
    'You are an internal execution role in the Content Factory worker pipeline. '
    'Produce concise, concrete markdown that can be compiled with other roles. '
    'Stay focused on the role purpose, build on prior role outputs, and hand off useful work.'
)

ROLE_FOCUS_PROMPTS: dict[str, str] = {
    'mike': (
        'Give the execution order, confirm the routing logic, note the immediate next step, '
        'and flag any dependency or sequencing risk.'
    ),
    'emma': (
        'Check that the work matches the product goal, point out anything that weakens the '
        'desired outcome, and state the product-safe direction.'
    ),
    'iris': (
        'Summarize the market context, ICP, key pains, and relevant trends or signals. '
        'Keep the research factual and useful for the next roles.'
    ),
    'sarah': (
        'Identify organic search angles, keyword intent, and topic framing that can rank or '
        'attract search traffic.'
    ),
    'adrian': (
        'Propose offers, hooks, and paid acquisition angles that are testable and attention-grabbing.'
    ),
    'alex': (
        'Turn the previous inputs into a usable draft, script, or content brief. '
        'Structure it clearly so the next step can use it directly.'
    ),
    'david': (
        'Check for inconsistencies, gaps, deviations, and efficiency issues in the current chain. '
        'Summarize what looks strong, what looks weak, and what should be corrected.'
    ),
    'bob': (
        'Focus on system-level issues, process breaks, integration risks, and architectural constraints. '
        'Recommend the cleanest structural fix or integration path.'
    ),
}

DEFAULT_ROLE_FOCUS = 'Focus on the role purpose and produce a concise, useful handoff.'


def _clean(value: Any, fallback: str = '') -> str:
    text = str(value or fallback).strip()
    return text


def build_role_user_prompt(*, job: dict[str, Any], role: dict[str, Any], stage: dict[str, Any], previous_outputs: list[dict[str, Any]]) -> str:
    role_id = _clean(role.get('role_id'))
    label = _clean(role.get('label'), role_id or 'Internal role')
    purpose = _clean(role.get('purpose'), 'No purpose provided')
    profile = _clean(job.get('execution_profile'), 'unknown')
    focus = ROLE_FOCUS_PROMPTS.get(role_id, DEFAULT_ROLE_FOCUS)
    brief_content = _clean(job.get('brief_content'))

    brief_section = f'Brief content:\n{brief_content}\n\n' if brief_content else 'Brief content: not provided\n\n'

    prior_lines: list[str] = []
    for previous in previous_outputs:
        previous_label = _clean(previous.get('label') or previous.get('role_id'))
        previous_output = _clean(previous.get('output'))
        if previous_label or previous_output:
            prior_lines.append(f'- {previous_label}: {previous_output[:220]}')
    prior_section = '\n'.join(prior_lines) if prior_lines else '- No prior role outputs yet.'

    return (
        f'Job title: {_clean(job.get("title"), "Untitled job")}\n'
        f'Execution profile: {profile}\n'
        f'Role: {label} ({role_id})\n'
        f'Role purpose: {purpose}\n'
        f'Role-specific focus: {focus}\n'
        f'Stage: {_clean(stage.get("stage_name"), "role-stage")}\n\n'
        f'{brief_section}'
        f'Previous role outputs:\n{prior_section}\n\n'
        'Write the next role contribution in markdown. '
        'Use a compact structure with a short headline and 2-4 bullets or short paragraphs. '
        'Do not mention policies, prompts, or that you are an AI.'
    )
