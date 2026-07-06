from types import SimpleNamespace

from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-29',
            'title': 'Packet 29 Smoke',
            'status': 'queued',
        }
        self.calls = []

    def claim_next_job(self):
        self.calls.append(('claim-next', None))
        return self.claim_result

    def heartbeat_job(self, job_id: str, stage_name: str | None = None):
        self.calls.append(('heartbeat', job_id, stage_name))
        return {'id': job_id, 'status': 'running', 'last_stage': stage_name}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id, error_message))
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


def test_run_loop_once_sends_stage_named_heartbeats(capsys):
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-29', None),
        ('heartbeat', 'job-29', 'render-output'),
        ('complete', 'job-29', 'stub-output-for-packet-29-smoke'),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker stage fetch-payload for job job-29' in out
    assert 'cf-worker stage render-output for job job-29' in out
