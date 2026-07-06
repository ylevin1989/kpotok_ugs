from types import SimpleNamespace

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


def test_persist_result_artifact_returns_stat_backed_metadata(monkeypatch):
    settings = SimpleNamespace(
        s3_endpoint='http://cf-minio:9000',
        s3_access_key='minio',
        s3_secret_key='change_me',
        s3_bucket='content-factory',
        s3_region='us-east-1',
        s3_use_ssl=False,
    )
    client = FakeStorageClient()
    monkeypatch.setattr(storage_module, 'get_storage_client', lambda _settings: client)

    artifact = persist_result_artifact(settings, 'stub-output-for-packet-32-smoke')

    assert artifact == {
        'key': 'jobs/stub-output-for-packet-32-smoke.txt',
        'url': 's3://content-factory/jobs/stub-output-for-packet-32-smoke.txt',
        'content_type': 'text/plain',
        'size_bytes': 58,
        'etag': 'etag-from-stat',
    }
    assert client.calls == [
        ('bucket_exists', 'content-factory'),
        ('put_object', 'content-factory', 'jobs/stub-output-for-packet-32-smoke.txt', b'stub-output-for-packet-32-smoke', 31, 'text/plain'),
        ('stat_object', 'content-factory', 'jobs/stub-output-for-packet-32-smoke.txt'),
    ]
