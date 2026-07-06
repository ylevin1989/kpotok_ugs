from types import SimpleNamespace

from app.main import process_job


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
        return f"{role['label']} role output"


def test_role_aware_output_requires_executor_and_compiles_previous_outputs(monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())

    job = {
        'id': 'job-99',
        'title': 'Packet 99 Executor Smoke',
        'status': 'queued',
        'execution_profile': 'seo_content',
        'internal_role_plan': [
            {'role_id': 'mike', 'label': 'Mike', 'purpose': 'Route execution'},
            {'role_id': 'emma', 'label': 'Emma', 'purpose': 'Protect product meaning'},
        ],
    }
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    result = process_job(settings, client, job)

    assert 'Mike role output' in result['result']
    assert 'Emma role output' in result['result']
    assert result['role_outputs'][0]['output'] == 'Mike role output'
    assert result['role_outputs'][1]['output'] == 'Emma role output'
    assert result['artifact']['key'] == 'jobs/internal-role-output-packet-99-executor-smoke.txt'
