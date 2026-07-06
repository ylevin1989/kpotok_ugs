from types import SimpleNamespace

from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-28',
            'title': 'Packet 28 Live Smoke',
            'status': 'queued',
        }
        self.calls = []

    def claim_next_job(self):
        self.calls.append(('claim-next', None))
        return self.claim_result

    def heartbeat_job(self, job_id: str, stage_name: str | None = None):
        self.calls.append(('heartbeat', job_id, stage_name))
        return {'id': job_id, 'status': 'running'}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id, error_message))
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


def test_run_loop_once_persists_process_result_via_complete_payload(capsys):
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    client = FakeWorkerApiClient()

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-28', None),
        ('heartbeat', 'job-28', 'render-output'),
        ('complete', 'job-28', 'stub-output-for-packet-28-live-smoke'),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker completed job job-28' in out
