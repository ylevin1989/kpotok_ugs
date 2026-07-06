from urllib.parse import urlparse

from fastapi import HTTPException, status
from minio import Minio

from app.core.config import Settings
from app.db.models.job import Job


def get_storage_client(settings: Settings) -> Minio:
    parsed = urlparse(settings.s3_endpoint)
    endpoint = parsed.netloc or parsed.path
    secure = settings.s3_use_ssl or parsed.scheme == 'https'
    return Minio(
        endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=secure,
        region=settings.s3_region,
    )


def expected_artifact_key(job: Job) -> str:
    return (
        f'organizations/{job.organization_id}/brands/{job.brand_id}/'
        f'jobs/{job.id}/artifacts/result.txt'
    )


def read_job_artifact(settings: Settings, job: Job) -> tuple[bytes, str]:
    if not job.output_artifact_key:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Job artifact is not available')
    if job.output_artifact_key != expected_artifact_key(job):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail='Job artifact key is outside the job tenant namespace',
        )

    client = get_storage_client(settings)
    response = client.get_object(settings.s3_bucket, job.output_artifact_key)
    try:
        payload = response.read()
    finally:
        response.close()
        response.release_conn()

    return payload, job.output_artifact_content_type or 'application/octet-stream'
