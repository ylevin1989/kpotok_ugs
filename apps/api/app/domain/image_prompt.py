from __future__ import annotations

import json
import os
import urllib.request
from typing import Any

_SYSTEM = (
    'Ты — арт-директор и prompt-инженер для генерации изображений. По тексту поста и данным бренда '
    'составь ОДИН короткий, конкретный промпт для image-модели (на английском, т.к. модели лучше его понимают). '
    'Опиши сцену, композицию, объект, свет, стиль и настроение, соответствующие бренду и посту. '
    'Фотореалистично, если это товар. НЕ добавляй текст/логотипы/буквы на изображении. '
    'Верни ТОЛЬКО JSON: {"image_prompt": "..."} без markdown.'
)


def _openrouter_chat(messages: list[dict[str, str]], *, json_mode: bool = True, temperature: float = 0.6) -> str:
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        raise RuntimeError('OPENROUTER_API_KEY is not configured')
    model = os.environ.get('OPENROUTER_MODEL', 'openai/gpt-5.4-mini')
    base_url = os.environ.get('OPENROUTER_BASE_URL', 'https://openrouter.ai/api/v1')
    payload: dict[str, Any] = {'model': model, 'messages': messages, 'temperature': temperature}
    if json_mode:
        payload['response_format'] = {'type': 'json_object'}
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
        'HTTP-Referer': 'https://app.uno-ai.pw',
        'X-Title': 'content-factory',
    }
    req = urllib.request.Request(base_url.rstrip('/') + '/chat/completions', data=json.dumps(payload).encode('utf-8'), headers=headers, method='POST')
    with urllib.request.urlopen(req, timeout=90) as r:
        data = json.loads(r.read().decode('utf-8'))
    return data['choices'][0]['message']['content']


def build_image_prompt(*, post_text: str, brand: Any, product: Any = None) -> str:
    brand_bits = [f'Brand: {getattr(brand, "name", "")}']
    pos = getattr(brand, 'positioning', None)
    if pos:
        brand_bits.append(f'Positioning: {pos}')
    tone = getattr(brand, 'tone_of_voice', None)
    if tone:
        brand_bits.append(f'Tone: {tone if isinstance(tone, str) else ", ".join(map(str, tone))}')
    if product is not None:
        brand_bits.append(f'Product: {getattr(product, "name", "")} — {getattr(product, "description", "")}')
    user = (
        'ДАННЫЕ БРЕНДА/ТОВАРА:\n' + '\n'.join(brand_bits) + '\n\n'
        'ТЕКСТ ПОСТА:\n' + (post_text or '')[:1500] + '\n\n'
        'Составь image-промпт для картинки к этому посту.'
    )
    content = _openrouter_chat([{'role': 'system', 'content': _SYSTEM}, {'role': 'user', 'content': user}])
    try:
        parsed = json.loads(content)
        prompt = parsed.get('image_prompt')
        if isinstance(prompt, str) and prompt.strip():
            return prompt.strip()
    except (json.JSONDecodeError, TypeError):
        pass
    # fallback: use raw content
    return (content or 'product photo, soft natural light, clean background').strip()[:800]
