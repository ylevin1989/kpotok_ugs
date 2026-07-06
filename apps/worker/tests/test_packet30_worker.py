from types import SimpleNamespace

from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-30',
            'title': 'Packet 30 Smoke',
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
        self.calls.append(('complete', job_id, output_text, artifact))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text, 'artifact': artifact}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id, error_message))
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


def test_run_loop_once_sends_output_artifact_reference(capsys):
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output,persist-artifact')
    client = FakeWorkerApiClient()

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-30', None),
        ('heartbeat', 'job-30', 'render-output'),
        ('heartbeat', 'job-30', 'persist-artifact'),
        ('complete', 'job-30', 'stub-output-for-packet-30-smoke', {
            'key': 'jobs/stub-output-for-packet-30-smoke.txt',
            'url': 's3://cf-artifacts/jobs/stub-output-for-packet-30-smoke.txt',
            'content_type': 'text/plain',
        }),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker stage persist-artifact for job job-30' in out
