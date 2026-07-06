from types import SimpleNamespace

from app.main import process_job, run_loop_once


class FakeWorkerApiClient:
    def __init__(self, claim_result=None):
        self.claim_result = claim_result or {'id': 'job-27', 'title': 'Payload smoke'}
        self.calls = []
        self.failed_payload = None

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
        self.calls.append(('fail', job_id))
        self.failed_payload = error_message
        return {'id': job_id, 'status': 'failed', 'error_message': error_message}


def test_process_job_runs_all_stub_stages_and_renews_lease_per_stage(capsys):
    client = FakeWorkerApiClient()
    settings = SimpleNamespace(worker_process_stages='fetch-payload,render-output')
    job = {'id': 'job-27', 'title': 'Payload smoke'}

    result = process_job(settings, client, job)

    assert result['job_id'] == 'job-27'
    assert result['title'] == 'Payload smoke'
    assert result['stages'] == ['fetch-payload', 'render-output']
    assert result['result'] == 'stub-output-for-payload-smoke'
    assert result['artifact'] == {
        'key': 'jobs/stub-output-for-payload-smoke.txt',
        'url': 's3://cf-artifacts/jobs/stub-output-for-payload-smoke.txt',
        'content_type': 'text/plain',
    }
    assert result['role_outputs'] == []
    assert client.calls == [
        ('heartbeat', 'job-27', 'fetch-payload'),
        ('heartbeat', 'job-27', 'render-output'),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker stage fetch-payload for job job-27' in out
    assert 'cf-worker stage render-output for job job-27' in out


def test_run_loop_once_completes_after_multi_stage_process(capsys):
    client = FakeWorkerApiClient({'id': 'job-42', 'title': 'Deep smoke'})
    settings = SimpleNamespace(worker_id='worker-alpha', worker_process_stages='fetch-payload,render-output,persist-artifact')

    outcome = run_loop_once(settings, client)

    assert outcome == 'completed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-42', None),
        ('heartbeat', 'job-42', 'render-output'),
        ('heartbeat', 'job-42', 'persist-artifact'),
        ('complete', 'job-42', 'stub-output-for-deep-smoke'),
    ]
    out = capsys.readouterr().out
    assert 'cf-worker claimed job job-42' in out
    assert 'cf-worker stage persist-artifact for job job-42' in out
    assert 'cf-worker completed job job-42' in out


def test_run_loop_once_fails_if_stage_processing_crashes_after_partial_progress(capsys):
    client = FakeWorkerApiClient({'id': 'job-66', 'title': 'Crash after stage'})
    settings = SimpleNamespace(worker_id='worker-alpha', worker_process_stages='fetch-payload,explode')

    def crash_after_first_stage(local_settings, local_client, job):
        process_job(SimpleNamespace(worker_process_stages='fetch-payload'), local_client, job)
        raise RuntimeError('stage pipeline exploded')

    outcome = run_loop_once(settings, client, process_job_fn=crash_after_first_stage)

    assert outcome == 'failed'
    assert client.calls == [
        ('claim-next', None),
        ('heartbeat', 'job-66', None),
        ('heartbeat', 'job-66', 'fetch-payload'),
        ('fail', 'job-66'),
    ]
    assert 'stage pipeline exploded' in client.failed_payload
    out = capsys.readouterr().out
    assert 'cf-worker failed job job-66' in out
