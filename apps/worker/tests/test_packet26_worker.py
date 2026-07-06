from types import SimpleNamespace

import httpx

from app.main import run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None, claim_exc=None):
        self.claim_result = claim_result
        self.claim_exc = claim_exc
        self.calls = []
        self.failed_payload = None

    def claim_next_job(self):
        self.calls.append(('claim-next', None))
        if self.claim_exc:
            raise self.claim_exc
        return self.claim_result

    def heartbeat_job(self, job_id: str, stage_name: str | None = None):
        self.calls.append(('heartbeat', job_id, stage_name))
        return {'id': job_id, 'status': 'running'}

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None):
        self.calls.append(('complete', job_id, output_text))
        return {'id': job_id, 'status': 'completed', 'output_text': output_text}

    def fail_job(self, job_id: str, error_message: str):
        self.calls.append(('fail', job_id))
        self.failed_payload = error_message
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


class NoContentResponse(httpx.Response):
    def __init__(self):
        request = httpx.Request('POST', 'http://worker.test/api/v1/jobs/claim-next')
        super().__init__(204, request=request)


def no_content_error() -> httpx.HTTPStatusError:
    response = NoContentResponse()
    return httpx.HTTPStatusError('no content', request=response.request, response=response)


def test_run_loop_once_claims_heartbeats_and_completes_job(capsys):
    client = FakeWorkerApiClient(claim_result={'id': 'job-123', 'title': 'Smoke job'})
    settings = SimpleNamespace(worker_id='worker-alpha')

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-123', None),
        ('heartbeat', 'job-123', 'render-output'),
        ('complete', 'job-123', 'stub-output-for-smoke-job'),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker claimed job job-123' in out
    assert 'cf-worker renewed lease for job job-123' in out
    assert 'cf-worker stage fetch-payload for job job-123' in out
    assert 'cf-worker stage render-output for job job-123' in out
    assert 'cf-worker completed job job-123' in out


def test_run_loop_once_returns_idle_when_queue_empty(capsys):
    client = FakeWorkerApiClient(claim_result=None)
    settings = SimpleNamespace(worker_id='worker-alpha')

    outcome = run_loop_once(settings, client)

    assert outcome == 'idle'
    assert client.calls == [('claim-next', None)]
    out = capsys.readouterr().out
    assert 'cf-worker idle: no queued jobs available' in out


def test_run_loop_once_fails_job_when_processing_crashes(capsys):
    client = FakeWorkerApiClient(claim_result={'id': 'job-999', 'title': 'Crashy job'})
    settings = SimpleNamespace(worker_id='worker-alpha')

    def crash(_settings, _client, job: dict) -> None:
        assert job['id'] == 'job-999'
        raise RuntimeError('synthetic processing crash')

    outcome = run_loop_once(settings, client, process_job_fn=crash)

    assert outcome == 'failed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-999', None),
        ('fail', 'job-999'),
    ]
    assert 'synthetic processing crash' in client.failed_payload
    out = capsys.readouterr().out
    assert 'cf-worker failed job job-999' in out
