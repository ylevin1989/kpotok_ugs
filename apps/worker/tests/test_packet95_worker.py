from types import SimpleNamespace

from app.main import process_job, run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-95',
            'title': 'Role aware smoke',
            'execution_profile': 'seo_content',
            'internal_role_plan': [
                {'role_id': 'mike', 'label': 'Mike', 'purpose': 'Route execution'},
                {'role_id': 'emma', 'label': 'Emma', 'purpose': 'Protect product meaning'},
                {'role_id': 'iris', 'label': 'Iris', 'purpose': 'Research inputs'},
            ],
        }
        self.calls = []
        self.failed_payload = None

    def claim_next_job(self):
        self.calls.append(('claim-next', None))
        return self.claim_result

    def heartbeat_job(self, job_id: str, stage_name: str | None = None, **payload):
        self.calls.append(('heartbeat', job_id, stage_name, payload))
        return {'id': job_id, 'status': 'running', 'last_stage': stage_name}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id))
        self.failed_payload = error_message
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


class FakeRoleExecutor:
    def execute_role(self, *, job, role, stage, previous_outputs):
        return f"{role['label']} output #{len(previous_outputs) + 1}"


def test_process_job_uses_internal_role_plan_for_role_aware_heartbeats(capsys, monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())
    client = FakeWorkerApiClient()
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    job = client.claim_result

    result = process_job(settings, client, job)

    assert result['stages'] == ['role:mike', 'role:emma', 'role:iris']
    assert client.calls == [
        ('heartbeat', 'job-95', 'role:mike', {
            'stage_label': 'Mike',
            'progress_percent': 33,
            'progress_message': 'Executing internal role Mike',
            'transition_tag': 'internal-role:mike',
            'worker_metadata': {
                'role_id': 'mike',
                'role_label': 'Mike',
                'execution_profile': 'seo_content',
                'role_index': 1,
                'role_count': 3,
            },
        }),
        ('heartbeat', 'job-95', 'role:emma', {
            'stage_label': 'Emma',
            'progress_percent': 67,
            'progress_message': 'Executing internal role Emma',
            'transition_tag': 'internal-role:emma',
            'worker_metadata': {
                'role_id': 'emma',
                'role_label': 'Emma',
                'execution_profile': 'seo_content',
                'role_index': 2,
                'role_count': 3,
            },
        }),
        ('heartbeat', 'job-95', 'role:iris', {
            'stage_label': 'Iris',
            'progress_percent': 100,
            'progress_message': 'Executing internal role Iris',
            'transition_tag': 'internal-role:iris',
            'worker_metadata': {
                'role_id': 'iris',
                'role_label': 'Iris',
                'execution_profile': 'seo_content',
                'role_index': 3,
                'role_count': 3,
            },
        }),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker stage role:mike for job job-95' in out
    assert 'cf-worker stage role:iris for job job-95' in out


def test_run_loop_once_completes_after_role_aware_process(capsys, monkeypatch):
    monkeypatch.setattr('app.main._build_role_executor', lambda settings: FakeRoleExecutor())
    client = FakeWorkerApiClient()
    settings = SimpleNamespace(worker_id='worker-alpha', worker_process_stages='fetch-payload,render-output')

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls[0] == ('claim-next', None)
    assert client.calls[1] == ('heartbeat', 'job-95', 'role:mike', {
        'stage_label': 'Mike',
        'progress_percent': 33,
        'progress_message': 'Executing internal role Mike',
        'transition_tag': 'internal-role:mike',
        'worker_metadata': {
            'role_id': 'mike',
            'role_label': 'Mike',
            'execution_profile': 'seo_content',
            'role_index': 1,
            'role_count': 3,
        },
    })
    assert client.calls[2][2] == 'role:emma'
    assert client.calls[3][2] == 'role:iris'
    assert client.calls[-1][0] == 'complete'
    assert client.calls[-1][1] == 'job-95'
    assert '# Internal role execution output' in client.calls[-1][2]
    out = capsys.readouterr().out
    assert 'cf-worker completed job job-95' in out
