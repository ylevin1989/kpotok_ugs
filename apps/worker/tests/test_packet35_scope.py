from types import SimpleNamespace

import app.main as main_module
from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {
            'id': 'job-35',
            'title': 'Packet 35 Scope Guard',
            'status': 'queued',
            'organization_id': 'org-35',
            'brand_id': 'brand-35',
            'brief_id': 'brief-35',
            'scope': {
                'organization_id': 'org-35',
                'brand_id': 'brand-35',
                'brief_id': 'brief-35',
            },
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


def test_run_loop_once_fails_when_artifact_key_escapes_job_scope(monkeypatch):
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output,persist-artifact', s3_bucket='content-factory')
    client = FakeWorkerApiClient()

    def fake_persist_result_artifact(_settings, _job, result_text: str):
        assert result_text == 'stub-output-for-packet-35-scope-guard'
        return {
            'key': 'organizations/other-org/brands/other-brand/jobs/other-job/artifacts/result.txt',
            'url': 's3://content-factory/organizations/other-org/brands/other-brand/jobs/other-job/artifacts/result.txt',
            'content_type': 'text/plain',
            'size_bytes': 56,
            'etag': 'etag-packet35-bad-scope',
        }

    monkeypatch.setattr(main_module, 'persist_result_artifact', fake_persist_result_artifact, raising=False)

    outcome = run_loop_once(settings, client)

    assert outcome == 'failed'
    assert ('complete', 'job-35', 'stub-output-for-packet-35-scope-guard', {
        'key': 'organizations/other-org/brands/other-brand/jobs/other-job/artifacts/result.txt',
        'url': 's3://content-factory/organizations/other-org/brands/other-brand/jobs/other-job/artifacts/result.txt',
        'content_type': 'text/plain',
        'size_bytes': 56,
        'etag': 'etag-packet35-bad-scope',
    }) not in client.calls
    assert client.calls[-1] == ('fail', 'job-35', 'processing error: artifact key escaped job scope')
