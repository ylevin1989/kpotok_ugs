from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import httpx

from app.config import Settings
from app.role_prompts import COMMON_SYSTEM_PROMPT, build_role_user_prompt


def _normalize_model_name(model: str) -> str:
    normalized = model.strip()
    if '/' in normalized:
        return normalized
    if normalized.startswith('gpt-'):
        return f'openai/{normalized}'
    return normalized


def _truncate(text: str, limit: int = 1200) -> str:
    cleaned = text.strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rstrip() + '…'


@dataclass
class OpenRouterRoleExecutor:
    settings: Settings
    client_factory: Callable[..., httpx.Client] = httpx.Client

    def __post_init__(self) -> None:
        api_key = getattr(self.settings, 'openrouter_api_key', None)
        if not api_key:
            raise RuntimeError('openrouter_api_key is required for role-aware LLM execution')
        self._api_key = api_key
        self._base_url = getattr(self.settings, 'openrouter_base_url', 'https://openrouter.ai/api/v1')
        self._model = _normalize_model_name(getattr(self.settings, 'openrouter_model', 'openai/gpt-5.4-mini'))
        self._site_url = getattr(self.settings, 'openrouter_site_url', 'https://app.uno-ai.pw')
        self._app_name = getattr(self.settings, 'openrouter_app_name', 'content-factory')

    def _headers(self) -> dict[str, str]:
        headers = {
            'Authorization': f'Bearer {self._api_key}',
            'Content-Type': 'application/json',
        }
        if self._site_url:
            headers['HTTP-Referer'] = self._site_url
        if self._app_name:
            headers['X-Title'] = self._app_name
        return headers

    def _build_messages(self, *, job: dict[str, Any], role: dict[str, Any], stage: dict[str, Any], previous_outputs: list[dict[str, Any]]) -> list[dict[str, str]]:
        user_prompt = build_role_user_prompt(job=job, role=role, stage=stage, previous_outputs=previous_outputs)
        return [
            {'role': 'system', 'content': COMMON_SYSTEM_PROMPT},
            {'role': 'user', 'content': user_prompt},
        ]

    def execute_role(self, *, job: dict[str, Any], role: dict[str, Any], stage: dict[str, Any], previous_outputs: list[dict[str, Any]]) -> str:
        payload = {
            'model': self._model,
            'messages': self._build_messages(job=job, role=role, stage=stage, previous_outputs=previous_outputs),
            'temperature': 0.2,
        }
        with self.client_factory(base_url=self._base_url, timeout=60.0, headers=self._headers()) as client:
            response = client.post('/chat/completions', json=payload)
            response.raise_for_status()
            data = response.json()
        try:
            content = data['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError('OpenRouter response did not include a completion message') from exc
        if not isinstance(content, str) or not content.strip():
            raise RuntimeError('OpenRouter response content was empty')
        return content.strip()
