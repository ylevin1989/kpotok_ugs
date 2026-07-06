from io import BytesIO
from urllib.parse import urlparse

from minio import Minio

from app.config import Settings


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


def expected_artifact_key(job) -> str | None:
    if isinstance(job, dict):
        job_id = job.get('id')
        organization_id = job.get('organization_id')
        brand_id = job.get('brand_id')
    else:
        job_id = getattr(job, 'id', None)
        organization_id = getattr(job, 'organization_id', None)
        brand_id = getattr(job, 'brand_id', None)
    if not job_id or not organization_id or not brand_id:
        return None
    return (
        f'organizations/{organization_id}/brands/{brand_id}/'
        f'jobs/{job_id}/artifacts/result.txt'
    )


def persist_result_artifact(settings: Settings, job_or_result_text, result_text: str | None = None) -> dict[str, str]:
    client = get_storage_client(settings)
    bucket = settings.s3_bucket
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)

    if result_text is None:
        job = None
        resolved_result_text = job_or_result_text
    else:
        job = job_or_result_text
        resolved_result_text = result_text

    key = expected_artifact_key(job) or f'jobs/{resolved_result_text}.txt'
    payload = resolved_result_text.encode()
    client.put_object(
        bucket,
        key,
        BytesIO(payload),
        length=len(payload),
        content_type='text/plain',
    )
    stat = client.stat_object(bucket, key)
    return {
        'key': key,
        'url': f's3://{bucket}/{key}',
        'content_type': 'text/plain',
        'size_bytes': stat.size,
        'etag': stat.etag,
    }
