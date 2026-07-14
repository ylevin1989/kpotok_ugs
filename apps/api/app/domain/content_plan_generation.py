from __future__ import annotations

import json
import os
import urllib.request
from datetime import date
from typing import Any

# Per-platform content methodology used to steer the LLM.
PLATFORM_PLAYBOOK: dict[str, str] = {
    'instagram': (
        'Instagram: 4-5 постов в неделю. Микс форматов: Reels (охват, 40%), карусели (польза/сохранения, 30%), '
        'одиночные посты (20%), Stories-идеи (10%). Первая строка — сильный хук. Визуал важен. CTA в конце.'
    ),
    'telegram': (
        'Telegram: 4-6 постов в неделю, можно ежедневно. Нативные текстовые посты, разговорный тон, '
        'польза и экспертность. Форматы: пост-мнение, разбор, кейс, чек-лист, анонс, вопрос аудитории.'
    ),
    'vk': (
        'VK: 4-5 постов в неделю. Форматы: пост, лонгрид/статья, клип, опрос, подборка. '
        'Сообщество и вовлечение, локальный контекст.'
    ),
    'youtube': (
        'YouTube: 1-2 видео в неделю + Shorts. Каждый пункт — сценарий видео: заголовок, хук первых 5 секунд, '
        'структура, CTA на подписку.'
    ),
    'tiktok': (
        'TikTok: 3-5 коротких видео в неделю. Сильный хук в первую секунду, тренды, динамика, звук. '
        'Каждый пункт — идея короткого видео со сценой и хуком.'
    ),
    'facebook': 'Facebook: 3-4 поста в неделю. Истории, польза, доверие, обсуждение.',
    'linkedin': 'LinkedIn (B2B): 3-4 поста в неделю. Экспертиза, кейсы, инсайты, лидерство мнений.',
}

DEFAULT_PLAYBOOK = (
    'Общая методология: 3-5 публикаций в неделю, разнообразие форматов и тем, '
    'воронка awareness -> trust -> sales, сильные хуки, конкретика и польза, ясный CTA.'
)

_SYSTEM = (
    'Ты — опытный контент-стратег. По данным о бренде, товаре и аудитории и методологии площадки '
    'составь осмысленный контент-план на период. План должен быть РАЗНООБРАЗНЫМ: разные темы, форматы и '
    'этапы воронки (awareness/trust/sales/engagement), а не однотипные записи. Пиши на языке контекста '
    '(если контекст на русском — на русском). Используй только факты из контекста, не выдумывай и не нарушай '
    'forbidden_claims. Верни ТОЛЬКО JSON-объект без markdown-обёрток.'
)


def _norm(platform: str) -> str:
    p = (platform or '').strip().lower()
    aliases = {
        'инстаграм': 'instagram', 'телеграм': 'telegram', 'телеграмм': 'telegram',
        'ютуб': 'youtube', 'тикток': 'tiktok', 'вконтакте': 'vk',
    }
    return aliases.get(p, p)


def _brand_block(brand: Any) -> str:
    dna = brand.dna_json if isinstance(getattr(brand, 'dna_json', None), dict) else {}
    lines = [f'- Название: {brand.name}']
    for label, val in (
        ('Позиционирование', getattr(brand, 'positioning', None)),
        ('Tone of voice', getattr(brand, 'tone_of_voice', None)),
        ('Разрешённые заявления', getattr(brand, 'allowed_claims', None)),
        ('Запрещённые заявления', getattr(brand, 'forbidden_claims', None)),
    ):
        if val:
            lines.append(f'- {label}: {val if isinstance(val, str) else ", ".join(map(str, val))}')
    if dna:
        lines.append(f'- Brand DNA: {json.dumps(dna, ensure_ascii=False)[:1500]}')
    return '\n'.join(lines)


def _product_block(product: Any) -> str:
    if product is None:
        return 'Товар: не задан (план на уровне бренда).'
    parts = [
        f'- Название: {product.name}',
        f'- Категория: {getattr(product, "category", "")}',
        f'- Описание: {getattr(product, "description", "")}',
    ]
    for label, val in (
        ('Особенности', getattr(product, 'features', None)),
        ('Выгоды', getattr(product, 'benefits', None)),
        ('Доказательства', getattr(product, 'proofs', None)),
        ('Возражения', getattr(product, 'objections', None)),
    ):
        if val:
            parts.append(f'- {label}: {", ".join(map(str, val))}')
    return '\n'.join(parts)


def _audience_block(aud: Any) -> str:
    if aud is None:
        return 'Аудитория: не задана.'
    parts = [f'- Сегмент: {aud.name}', f'- Описание: {getattr(aud, "description", "")}']
    for label, val in (
        ('Боли', getattr(aud, 'pain_points', None)),
        ('Цели', getattr(aud, 'goals', None)),
        ('Возражения', getattr(aud, 'objections', None)),
    ):
        if val:
            parts.append(f'- {label}: {", ".join(map(str, val))}')
    return '\n'.join(parts)


def generate_plan_items(*, brand: Any, product: Any, audience: Any, platform: str, start: date, end: date, goal: str) -> list[dict[str, Any]]:
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise RuntimeError('OPENROUTER_API_KEY is not configured for the API service')
    model = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-5.4-mini')
    base_url = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    playbook = PLATFORM_PLAYBOOK.get(_norm(platform), DEFAULT_PLAYBOOK)
    days = (end - start).days + 1

    contract = (
        'Верни строго JSON: {"plan": [{"date": "YYYY-MM-DD", "title": "...", '
        '"content_type": "post|reel|story|carousel|video|article", '
        '"funnel_stage": "awareness|trust|sales|engagement", '
        '"brief": "идея + хук, 1-3 предложения"}]}. '
        'Даты — только внутри указанного периода. Максимум 1-3 публикации в день.'
    )
    user = (
        f'ПЛОЩАДКА: {platform}\nМЕТОДОЛОГИЯ ПЛОЩАДКИ: {playbook}\n'
        f'ПЕРИОД: с {start.isoformat()} по {end.isoformat()} ({days} дней).\n'
        f'ГЛАВНАЯ ЦЕЛЬ ПЕРИОДА: {goal or "рост доверия и продаж"}\n\n'
        f'БРЕНД:\n{_brand_block(brand)}\n\n'
        f'ТОВАР:\n{_product_block(product)}\n\n'
        f'АУДИТОРИЯ:\n{_audience_block(audience)}\n\n'
        'Составь план публикаций на период по методологии площадки (НЕ обязательно каждый день — '
        'соблюдай разумную частоту площадки). Для каждой публикации верни дату в пределах периода, '
        'рабочий заголовок/тему, тип контента, этап воронки и краткий бриф с идеей и хуком.\n\n'
        + contract
    )
    payload = {
        'model': model,
        'messages': [{'role': 'system', 'content': _SYSTEM}, {'role': 'user', 'content': user}],
        'temperature': 0.7,
        'response_format': {'type': 'json_object'},
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://app.uno-ai.pw',
        'X-Title': 'content-factory',
    }
    req = urllib.request.Request(
        base_url.rstrip('/') + '/chat/completions',
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method='POST',
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        data = json.loads(r.read().decode('utf-8'))
    content = data['choices'][0]['message']['content']
    parsed = json.loads(content)
    plan = parsed.get('plan') if isinstance(parsed, dict) else None
    if not isinstance(plan, list) or not plan:
        raise RuntimeError('LLM did not return a valid plan array')
    out: list[dict[str, Any]] = []
    for it in plan:
        if not isinstance(it, dict):
            continue
        d = str(it.get('date') or '').strip()
        title = str(it.get('title') or '').strip()
        if not d or not title:
            continue
        out.append({
            'date': d,
            'title': title,
            'content_type': str(it.get('content_type') or 'post').strip(),
            'funnel_stage': str(it.get('funnel_stage') or '').strip(),
            'brief': str(it.get('brief') or '').strip(),
        })
    if not out:
        raise RuntimeError('LLM plan had no usable items')
    return out
