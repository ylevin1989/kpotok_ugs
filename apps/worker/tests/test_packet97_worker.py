from types import SimpleNamespace

from app.main import process_job, run_loop_once


ROLE_AWARE_JOB = {
    'id': 'job-97',
    'title': 'Packet 97 Role Brain Smoke',
    'status': 'queued',
    'execution_profile': 'seo_content',
    'internal_role_plan': [
        {'role_id': 'mike', 'label': 'Mike', 'purpose': 'Route execution'},
        {'role_id': 'emma', 'label': 'Emma', 'purpose': 'Protect product meaning'},
        {'role_id': 'iris', 'label': 'Iris', 'purpose': 'Research inputs'},
    ],
}


class FakeWorkerApiClient:
    def __init__(self):
        self.calls = []

    def claim_next_job(self):
        self.calls.append(('claim-next', None))
        return dict(ROLE_AWARE_JOB)

    def heartbeat_job(self, job_id: str, stage_name: str | None = None, **payload):
        self.calls.append(('heartbeat', job_id, stage_name, payload))
        return {'id': job_id, 'status': 'running', 'last_stage': stage_name}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text, artifact))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text, 'artifact': artifact}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id, error_message))
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


class FakeRoleExecutor:
    def execute_role(self, *, job, role, stage, previous_outputs):
        return f"{role['label']} output #{len(previous_outputs) + 1} for {stage['stage_name']}"


def test_process_job_compiles_role_specific_output_for_internal_role_plan(monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())

    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    result = process_job(settings, client, dict(ROLE_AWARE_JOB))

    output = result['result']
    assert 'stub-output' not in output
    assert '# Internal role execution output' in output
    assert '**Execution profile:** `seo_content`' in output
    assert '**Job:** Packet 97 Role Brain Smoke' in output
    assert '## 1. Mike (`mike`)' in output
    assert 'Mike output #1 for role:mike' in output
    assert '## 2. Emma (`emma`)' in output
    assert 'Emma output #2 for role:emma' in output
    assert '## 3. Iris (`iris`)' in output
    assert 'Iris output #3 for role:iris' in output
    assert '## Final compiled result' in output
    assert 'Mike -> Emma -> Iris' in output
    assert result['stages'] == ['role:mike', 'role:emma', 'role:iris']


def test_run_loop_once_completes_role_aware_job_with_compiled_role_output(monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())

    settings = SimpleNamespace(worker_id='worker-alpha', worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    complete_call = client.calls[-1]
    assert complete_call[0] == 'complete'
    assert complete_call[1] == 'job-97'
    assert '# Internal role execution output' in complete_call[2]
    assert 'stub-output' not in complete_call[2]
    assert complete_call[3]['key'] == 'jobs/internal-role-output-packet-97-role-brain-smoke.txt'
    assert complete_call[3]['url'] == 's3://cf-artifacts/jobs/internal-role-output-packet-97-role-brain-smoke.txt'
    assert complete_call[3]['content_type'] == 'text/plain'
    assert [call[2] for call in client.calls if call[0] == 'heartbeat'] == ['role:mike', 'role:emma', 'role:iris']


def test_legacy_generic_jobs_keep_existing_stub_output_contract():
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()
    legacy_job = {'id': 'job-legacy', 'title': 'Legacy Generic Smoke', 'status': 'queued'}

    result = process_job(settings, client, legacy_job)

    assert result['result'] == 'stub-output-for-legacy-generic-smoke'
    assert result['stages'] == ['fetch-payload', 'render-output']
