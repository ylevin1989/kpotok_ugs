from __future__ import annotations

import json
from typing import Any

COMMON_SYSTEM_PROMPT = (
    'You are an internal execution role in the Content Factory worker pipeline. '
    'Use only the provided context. Do not invent facts. Respect forbidden_claims and any other explicit exclusions. '
    'If a fact is not present in the context, omit it. '
    'When you are the final stage, return content_version.structured_json as a single JSON object '
    'with keys title, text, short_text, cta, visual_task, image_prompt, and risks, '
    'plus body_markdown as the publishable markdown body.'
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


def _list_text(values: Any, fallback: str = 'not provided') -> str:
    if isinstance(values, list) and values:
        return '; '.join(_clean(item) for item in values if _clean(item))
    if isinstance(values, str) and values.strip():
        return values.strip()
    return fallback


def _append_sections(lines: list[str], heading: str, entries: list[tuple[str, Any]]) -> None:
    meaningful = [(label, value) for label, value in entries if value not in (None, '', [], {})]
    if not meaningful:
        return
    lines.append(f'{heading}:')
    for label, value in meaningful:
        if isinstance(value, list):
            lines.append(f'- {label}: {_list_text(value)}')
        else:
            lines.append(f'- {label}: {_clean(value)}')
    lines.append('')


def _format_context_section(context_payload: dict[str, Any]) -> str:
    lines: list[str] = ['Generation context:']

    brand = context_payload.get('brand_context') if isinstance(context_payload.get('brand_context'), dict) else {}
    brand_dna = brand.get('dna_json') if isinstance(brand.get('dna_json'), dict) else {}
    brand_tone = brand_dna.get('tone_of_voice') or brand_dna.get('tone')
    if isinstance(brand_tone, list):
        brand_tone = ', '.join(_clean(item) for item in brand_tone if _clean(item))
    brand_positioning = brand_dna.get('positioning')
    allowed_claims = brand_dna.get('allowed_claims')
    forbidden_claims = brand_dna.get('forbidden_claims')

    lines.extend([
        'Brand:',
        f"- name: {_clean(brand.get('name'), 'not provided')}",
    ])
    if brand_positioning:
        lines.append(f'- positioning: {_clean(brand_positioning)}')
    if brand_tone:
        lines.append(f'- tone: {_clean(brand_tone)}')
    if allowed_claims:
        lines.append(f'- allowed claims: {_list_text(allowed_claims)}')
    if forbidden_claims:
        lines.append(f'- forbidden claims: {_list_text(forbidden_claims)}')
    lines.append('')

    product = context_payload.get('product_context') if isinstance(context_payload.get('product_context'), dict) else {}
    if product:
        product_lines = ['Product:']
        product_lines.append(f"- name: {_clean(product.get('name'), 'not provided')}")
        if product.get('category'):
            product_lines.append(f"- category: {_clean(product.get('category'))}")
        if product.get('description'):
            product_lines.append(f"- description: {_clean(product.get('description'))}")
        if product.get('features'):
            product_lines.append(f"- features: {_list_text(product.get('features'))}")
        if product.get('benefits'):
            product_lines.append(f"- benefits: {_list_text(product.get('benefits'))}")
        if product.get('proofs'):
            product_lines.append(f"- proofs: {_list_text(product.get('proofs'))}")
        if product.get('objections'):
            product_lines.append(f"- objections: {_list_text(product.get('objections'))}")
        if product.get('restrictions'):
            product_lines.append(f"- restrictions: {_list_text(product.get('restrictions'))}")
        if isinstance(product.get('dna_json'), dict) and product['dna_json']:
            product_lines.append(f"- dna_json: {json.dumps(product['dna_json'], ensure_ascii=False, sort_keys=True)}")
        lines.extend(product_lines)
        lines.append('')

    audience = context_payload.get('audience_context') if isinstance(context_payload.get('audience_context'), dict) else {}
    if audience:
        audience_lines = ['Audience:']
        audience_lines.append(f"- name: {_clean(audience.get('name'), 'not provided')}")
        if audience.get('description'):
            audience_lines.append(f"- description: {_clean(audience.get('description'))}")
        if audience.get('pain_points'):
            audience_lines.append(f"- pain points: {_list_text(audience.get('pain_points'))}")
        if audience.get('goals'):
            audience_lines.append(f"- goals: {_list_text(audience.get('goals'))}")
        if audience.get('objections'):
            audience_lines.append(f"- objections: {_list_text(audience.get('objections'))}")
        if audience.get('keywords'):
            audience_lines.append(f"- keywords: {_list_text(audience.get('keywords'))}")
        lines.extend(audience_lines)
        lines.append('')

    channel = context_payload.get('channel') if isinstance(context_payload.get('channel'), dict) else {}
    if channel:
        lines.extend([
            'Channel:',
            f"- platform: {_clean(channel.get('platform'), 'not provided')}",
            f"- goal: {_clean(channel.get('goal'), 'not provided')}",
        ])
        if channel.get('date'):
            lines.append(f"- date: {_clean(channel.get('date'))}")
        lines.append('')

    task = context_payload.get('task') if isinstance(context_payload.get('task'), dict) else {}
    if task:
        lines.extend([
            'Task:',
            f"- title: {_clean(task.get('title'), 'not provided')}",
            f"- content type: {_clean(task.get('content_type'), 'not provided')}",
            f"- goal: {_clean(task.get('goal'), 'not provided')}",
            f"- scope: {_clean(task.get('scope'), 'not provided')}",
        ])
        if task.get('platform'):
            lines.append(f"- platform: {_clean(task.get('platform'))}")
        lines.append('')

    return '\n'.join(lines).rstrip() + '\n\n'


def _final_output_contract() -> str:
    return (
        'Final output contract:\n'
        '- Return a single JSON object only. No markdown fences, no commentary.\n'
        '- Required keys: title, text, short_text, cta, visual_task, image_prompt, risks, body_markdown.\n'
        '- title: concise content title.\n'
        '- text: the main copy/body text.\n'
        '- short_text: shorter variant or teaser text.\n'
        '- cta: a single call to action.\n'
        '- visual_task: a brief creative instruction for the visual team.\n'
        '- image_prompt: a concrete image-generation prompt.\n'
        '- risks: a JSON array or compact string listing content risks, policy risks, or claim risks.\n'
        '- body_markdown: the publishable markdown body ready for content_version.body_markdown.\n'
        '- Use only facts present in the provided context and never invent claims that conflict with forbidden_claims.\n'
        '- Ensure body_markdown and the structured fields agree with each other.\n\n'
    )


def build_role_user_prompt(*, job: dict[str, Any], role: dict[str, Any], stage: dict[str, Any], previous_outputs: list[dict[str, Any]]) -> str:
    role_id = _clean(role.get('role_id'))
    label = _clean(role.get('label'), role_id or 'Internal role')
    purpose = _clean(role.get('purpose'), 'No purpose provided')
    profile = _clean(job.get('execution_profile'), 'unknown')
    focus = ROLE_FOCUS_PROMPTS.get(role_id, DEFAULT_ROLE_FOCUS)
    context_payload = job.get('context')
    context_section = ''
    if isinstance(context_payload, dict) and context_payload:
        context_section = _format_context_section(context_payload)
    elif _clean(job.get('brief_content')):
        context_section = f"Brief content:\n{_clean(job.get('brief_content'))}\n\n"

    prior_lines: list[str] = []
    for previous in previous_outputs:
        previous_label = _clean(previous.get('label') or previous.get('role_id'))
        previous_output = _clean(previous.get('output'))
        if previous_label or previous_output:
            prior_lines.append(f'- {previous_label}: {previous_output[:220]}')
    prior_section = '\n'.join(prior_lines) if prior_lines else '- No prior role outputs yet.'

    final_stage = bool(stage.get('is_final'))
    output_section = _final_output_contract() if final_stage else (
        'Write the next role contribution in markdown. '
        'Use a compact structure with a short headline and 2-4 bullets or short paragraphs. '
        'Do not mention policies, prompts, or that you are an AI.\n\n'
    )

    return (
        f'Job title: {_clean(job.get("title"), "Untitled job")}\n'
        f'Execution profile: {profile}\n'
        f'Role: {label} ({role_id})\n'
        f'Role purpose: {purpose}\n'
        f'Role-specific focus: {focus}\n'
        f'Stage: {_clean(stage.get("stage_name"), "role-stage")}\n\n'
        f'{context_section}'
        f'Previous role outputs:\n{prior_section}\n\n'
        f'{output_section}'
    )


# --- Final deliverable assembler (added by ops: produce a clean ТЗ 20.4 deliverable) ---

ASSEMBLER_SYSTEM_PROMPT = (
    'You are the final content assembler for a brand content studio. '
    'Your job is to turn the internal team notes and the provided context into a single, '
    'ready-to-publish piece of content for the given channel. '
    'Write natural, publishable copy in the SAME language as the brand/product/audience context '
    '(if the context is in Russian, write in Russian). '
    'Ground every claim in the provided product facts, brand positioning and tone. '
    'Never invent facts or make claims that conflict with forbidden_claims. '
    'Do NOT expose internal role notes, analysis, "strong/weak points", or that you are an AI. '
    'Return ONLY a single JSON object, no markdown fences, no commentary.'
)


def build_assembler_user_prompt(*, job: dict[str, Any], role_outputs: list[dict[str, Any]]) -> str:
    context_payload = job.get('context')
    context_section = ''
    if isinstance(context_payload, dict) and context_payload:
        context_section = _format_context_section(context_payload)
    elif _clean(job.get('brief_content')):
        context_section = f"Brief content:\n{_clean(job.get('brief_content'))}\n\n"

    notes_lines: list[str] = []
    for item in role_outputs:
        label = _clean(item.get('label') or item.get('role_id'))
        output = _clean(item.get('output'))
        if label or output:
            notes_lines.append(f'- {label}: {output}')
    notes_section = '\n'.join(notes_lines) if notes_lines else '- No internal notes.'

    return (
        f'Job title: {_clean(job.get("title"), "Untitled job")}\n'
        f'Execution profile: {_clean(job.get("execution_profile"), "unknown")}\n\n'
        f'{context_section}'
        f'Internal team notes (background only, do not reproduce verbatim):\n{notes_section}\n\n'
        'Now produce the FINAL publishable deliverable for the channel above.\n\n'
        f'{_final_output_contract()}'
    )
