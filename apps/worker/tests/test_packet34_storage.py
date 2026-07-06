from types import SimpleNamespace
from uuid import uuid4

import app.storage as storage_module
from app.storage import persist_result_artifact


class FakeStatObject:
    def __init__(self, object_name: str, size: int, etag: str):
        self.object_name = object_name
        self.size = size
        self.etag = etag


class FakeStorageClient:
    def __init__(self):
        self.calls = []

    def bucket_exists(self, bucket: str) -> bool:
        self.calls.append(('bucket_exists', bucket))
        return True

    def put_object(self, bucket: str, key: str, data, length: int, content_type: str):
        payload = data.read()
        self.calls.append(('put_object', bucket, key, payload, length, content_type))
        return {'ok': True}

    def stat_object(self, bucket: str, key: str):
        self.calls.append(('stat_object', bucket, key))
        return FakeStatObject(key, 58, 'etag-from-stat')


def test_persist_result_artifact_uses_tenant_aware_namespace(monkeypatch):
    settings = SimpleNamespace(
        s3_endpoint='http://cf-minio:9000',
        s3_access_key='minio',
        s3_secret_key='change_me',
        s3_bucket='content-factory',
        s3_region='us-east-1',
        s3_use_ssl=False,
    )
    job = {
        'id': str(uuid4()),
        'organization_id': str(uuid4()),
        'brand_id': str(uuid4()),
    }
    client = FakeStorageClient()
    monkeypatch.setattr(storage_module, 'get_storage_client', lambda _settings: client)

    artifact = persist_result_artifact(settings, job, 'stub-output-for-packet-34-smoke')

    expected_key = (
        f"organizations/{job['organization_id']}/brands/{job['brand_id']}/"
        f"jobs/{job['id']}/artifacts/result.txt"
    )
    assert artifact == {
        'key': expected_key,
        'url': f's3://content-factory/{expected_key}',
        'content_type': 'text/plain',
        'size_bytes': 58,
        'etag': 'etag-from-stat',
    }
    assert client.calls == [
        ('bucket_exists', 'content-factory'),
        ('put_object', 'content-factory', expected_key, b'stub-output-for-packet-34-smoke', 31, 'text/plain'),
        ('stat_object', 'content-factory', expected_key),
    ]
