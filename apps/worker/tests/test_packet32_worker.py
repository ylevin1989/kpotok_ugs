from types import SimpleNamespace

import app.main as main_module
from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-32',
            'title': 'Packet 32 Smoke',
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


def test_run_loop_once_sends_storage_artifact_metadata(monkeypatch, capsys):
    settings = SimpleNamespace(
        worker_process_stages='fetch-payload,render-output,persist-artifact',
        s3_bucket='content-factory',
    )
    client = FakeWorkerApiClient()

    def fake_persist_result_artifact(_settings, result_text: str):
        assert result_text == 'stub-output-for-packet-32-smoke'
        return {
            'key': 'jobs/uploaded-with-metadata.txt',
            'url': 's3://content-factory/jobs/uploaded-with-metadata.txt',
            'content_type': 'text/plain',
            'size_bytes': 58,
            'etag': 'etag-packet32-worker',
        }

    monkeypatch.setattr(main_module, 'persist_result_artifact', fake_persist_result_artifact, raising=False)

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-32', None),
        ('heartbeat', 'job-32', 'render-output'),
        ('heartbeat', 'job-32', 'persist-artifact'),
        ('complete', 'job-32', 'stub-output-for-packet-32-smoke', {
            'key': 'jobs/uploaded-with-metadata.txt',
            'url': 's3://content-factory/jobs/uploaded-with-metadata.txt',
            'content_type': 'text/plain',
            'size_bytes': 58,
            'etag': 'etag-packet32-worker',
        }),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker stage persist-artifact for job job-32' in out
