from __future__ import annotations

import json
import os
import time
import urllib.request
import urllib.error

KIE_BASE = 'https://api.kie.ai/api/v1'
DEFAULT_IMAGE_MODEL = 'google/nano-banana'


def _headers() -> dict[str, str]:
    key = os.environ.get('KIE_API_KEY')
    if not key:
        raise RuntimeError('KIE_API_KEY is not configured')
    return {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}


def _post(path: str, body: dict) -> dict:
    req = urllib.request.Request(KIE_BASE + path, data=json.dumps(body).encode('utf-8'), headers=_headers(), method='POST')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def _get(path: str) -> dict:
    req = urllib.request.Request(KIE_BASE + path, headers=_headers(), method='GET')
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8'))


def generate_image_url(prompt: str, *, model: str | None = None, image_size: str = '1:1', poll_seconds: int = 120) -> str:
    """Create an image task on kie.ai and poll until a result URL is available."""
    model = model or os.environ.get('KIE_IMAGE_MODEL', DEFAULT_IMAGE_MODEL)
    created = _post('/jobs/createTask', {'model': model, 'input': {'prompt': prompt, 'image_size': image_size}})
    if created.get('code') != 200:
        raise RuntimeError(f'kie.ai createTask failed: {created.get("msg")}')
    task_id = (created.get('data') or {}).get('taskId')
    if not task_id:
        raise RuntimeError('kie.ai did not return a taskId')

    deadline = time.time() + poll_seconds
    while time.time() < deadline:
        time.sleep(5)
        info = _get(f'/jobs/recordInfo?taskId={task_id}')
        data = info.get('data') or {}
        state = data.get('state')
        if state == 'success':
            result_json = data.get('resultJson') or '{}'
            try:
                result = json.loads(result_json)
            except (json.JSONDecodeError, TypeError):
                raise RuntimeError('kie.ai returned an unparseable result')
            urls = result.get('resultUrls') or []
            if not urls:
                raise RuntimeError('kie.ai result had no image URLs')
            return urls[0]
        if state == 'fail':
            raise RuntimeError(f'kie.ai generation failed: {data.get("failMsg") or "unknown error"}')
    raise RuntimeError('kie.ai generation timed out')


def download_bytes(url: str, *, timeout: int = 60) -> tuple[bytes, str]:
    req = urllib.request.Request(
        url,
        method='GET',
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0 Safari/537.36',
            'Accept': 'image/avif,image/webp,image/png,image/*,*/*;q=0.8',
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        content_type = r.headers.get('Content-Type', 'image/png')
        return r.read(), content_type
