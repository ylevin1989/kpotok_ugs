import httpx

from app.config import Settings


class WorkerApiClient:
    def __init__(self, settings: Settings):
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            'X-Worker-Token': self._settings.worker_token,
            'X-Worker-Id': self._settings.worker_id,
        }

    def claim_next_job(self) -> dict | None:
        return self._post('/api/v1/jobs/claim-next')

    def claim_job(self, job_id: str) -> dict:
        return self._post(f'/api/v1/jobs/{job_id}/claim')

    def heartbeat_job(
        self,
        job_id: str,
        stage_name: str | None = None,
        *,
        stage_label: str | None = None,
        progress_percent: int | None = None,
        progress_message: str | None = None,
        transition_tag: str | None = None,
        worker_metadata: dict | None = None,
    ) -> dict:
        payload: dict | None = None
        if any(value is not None for value in (stage_name, stage_label, progress_percent, progress_message, transition_tag, worker_metadata)):
            payload = {}
            if stage_name is not None:
                payload['stage_name'] = stage_name
            if stage_label is not None:
                payload['stage_label'] = stage_label
            if progress_percent is not None:
                payload['progress_percent'] = progress_percent
            if progress_message is not None:
                payload['progress_message'] = progress_message
            if transition_tag is not None:
                payload['transition_tag'] = transition_tag
            if worker_metadata is not None:
                payload['worker_metadata'] = worker_metadata
        return self._post(f'/api/v1/jobs/{job_id}/heartbeat', payload)

    def complete_job(self, job_id: str, output_text: str | None = None, artifact: dict | None = None) -> dict:
        payload = {'output_text': output_text} if output_text is not None else {}
        if artifact is not None:
            payload['output_artifact_key'] = artifact.get('key')
            payload['output_artifact_url'] = artifact.get('url')
            payload['output_artifact_content_type'] = artifact.get('content_type')
            payload['output_artifact_size_bytes'] = artifact.get('size_bytes')
            payload['output_artifact_etag'] = artifact.get('etag')
        return self._post(f'/api/v1/jobs/{job_id}/complete', payload or None)

    def fail_job(self, job_id: str, error_message: str) -> dict:
        return self._post(f'/api/v1/jobs/{job_id}/fail', {'error_message': error_message})

    def _post(self, path: str, payload: dict | None = None) -> dict | None:
        with httpx.Client(base_url=self._settings.cf_api_base_url, timeout=30.0) as client:
            response = client.post(path, json=payload, headers=self._headers())
            if response.status_code == 204:
                return None
            response.raise_for_status()
            return response.json()
