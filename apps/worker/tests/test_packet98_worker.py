from types import SimpleNamespace

import httpx

from app.llm_client import OpenRouterRoleExecutor
from app.main import process_job


ROLE_AWARE_JOB = {
    'id': 'job-98',
    'title': 'Packet 98 LLM Role Brain Smoke',
    'status': 'queued',
    'execution_profile': 'seo_content',
    'internal_role_plan': [
        {'role_id': 'mike', 'label': 'Mike', 'purpose': 'Route execution'},
        {'role_id': 'emma', 'label': 'Emma', 'purpose': 'Protect product meaning'},
    ],
}


class FakeWorkerApiClient:
    def __init__(self):
        self.calls = []

    def heartbeat_job(self, job_id: str, stage_name: str | None = None, **payload):
        self.calls.append(('heartbeat', job_id, stage_name, payload))
        return {'id': job_id, 'status': 'running', 'last_stage': stage_name}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text, artifact))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text, 'artifact': artifact}


class FakeRoleExecutor:
    def execute_role(self, *, job, role, stage, previous_outputs):
        return f"{role['label']} role output #{len(previous_outputs) + 1}"


def test_openrouter_role_executor_builds_chat_completions_request_and_returns_output():
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured['method'] = request.method
        captured['path'] = request.url.path
        captured['headers'] = {key.lower(): value for key, value in request.headers.items()}
        captured['json'] = request.content.decode('utf-8')
        return httpx.Response(
            200,
            json={
                'choices': [
                    {'message': {'content': '## role output\n- first\n- second'}},
                ],
            },
        )

    transport = httpx.MockTransport(handler)
    settings = SimpleNamespace(
        openrouter_api_key='test-key',
        openrouter_base_url='https://openrouter.test/v1',
        openrouter_model='gpt-5.4-mini',
        openrouter_site_url='https://app.uno-ai.pw',
        openrouter_app_name='content-factory',
    )
    executor = OpenRouterRoleExecutor(
        settings,
        client_factory=lambda **kwargs: httpx.Client(transport=transport, **kwargs),
    )

    output = executor.execute_role(
        job=ROLE_AWARE_JOB,
        role=ROLE_AWARE_JOB['internal_role_plan'][0],
        stage={'stage_name': 'role:mike'},
        previous_outputs=[],
    )

    assert output == '## role output\n- first\n- second'
    assert captured['method'] == 'POST'
    assert captured['path'] == '/v1/chat/completions'
    assert captured['headers']['authorization'] == 'Bearer test-key'
    assert captured['headers']['http-referer'] == 'https://app.uno-ai.pw'
    assert captured['headers']['x-title'] == 'content-factory'
    assert 'openai/gpt-5.4-mini' in captured['json']
    assert 'Role-specific focus: Give the execution order' in captured['json']


def test_process_job_uses_llm_role_outputs_and_compiles_role_specific_output(monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())

    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    result = process_job(settings, client, dict(ROLE_AWARE_JOB))

    assert 'stub-output' not in result['result']
    assert '# Internal role execution output' in result['result']
    assert 'Mike role output #1' in result['result']
    assert 'Emma role output #2' in result['result']
    assert 'Mike -> Emma' in result['result']
    assert result['stages'] == ['role:mike', 'role:emma']
    assert result['role_outputs'][0]['output'] == 'Mike role output #1'
    assert result['role_outputs'][1]['output'] == 'Emma role output #2'


def test_legacy_generic_jobs_keep_existing_stub_output_contract():
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()
    legacy_job = {'id': 'job-legacy', 'title': 'Legacy Generic Smoke', 'status': 'queued'}

    result = process_job(settings, client, legacy_job)

    assert result['result'] == 'stub-output-for-legacy-generic-smoke'
    assert result['stages'] == ['fetch-payload', 'render-output']
