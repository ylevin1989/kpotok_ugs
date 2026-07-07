import io
import json
import zipfile
from datetime import date

from app import storage as storage_module
from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal


class FakeObjectResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self) -> bytes:
        return self._payload

    def close(self) -> None:
        return None

    def release_conn(self) -> None:
        return None


class FakeStorageClient:
    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put_object(self, bucket_name: str, object_name: str, data, length: int, content_type: str | None = None):
        payload = data.read() if hasattr(data, 'read') else data
        assert len(payload) == length
        self.objects[f'{bucket_name}/{object_name}'] = payload
        return {'etag': 'fake-etag', 'content_type': content_type}

    def get_object(self, bucket_name: str, object_name: str):
        return FakeObjectResponse(self.objects[f'{bucket_name}/{object_name}'])


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_export_fixture():
    owner = seed_user('owner-p204@example.com')
    outsider = seed_user('outsider-p204@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet204', slug='uno-packet204', status=OrganizationStatus.ACTIVE)
    outsider_org = Organization(name='Other Packet204', slug='other-packet204', status=OrganizationStatus.ACTIVE)
    db.add_all([org, outsider_org])
    db.flush()

    brand = Brand(organization_id=org.id, name='Rocket Tea 204', slug='rocket-tea-p204')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='rocket-tea-p204-sku',
        name='Rocket Tea Product 204',
        category='tea',
        description='Packet 204 product',
    )
    db.add(product)
    db.flush()

    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        date=date(2026, 7, 7),
        title='Export Plan 204',
        platform='instagram',
        content_type='post',
        goal='Drive approvals',
        status='approved',
    )
    db.add(plan)
    db.flush()

    approved_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=plan.id,
        scope='product',
        platform='instagram',
        content_type='post',
        goal='Approved goal',
        title='Approved item',
        status='approved',
        quality_score=95,
    )
    draft_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=plan.id,
        scope='product',
        platform='instagram',
        content_type='post',
        goal='Draft goal',
        title='Draft item',
        status='draft',
        quality_score=20,
    )
    db.add_all([approved_item, draft_item])
    db.flush()

    approved_version = ContentVersion(
        organization_id=org.id,
        content_item_id=approved_item.id,
        version_number=1,
        body_markdown='# Approved headline\n\nBody for approved export.',
        structured_json={'blocks': [{'type': 'paragraph', 'text': 'Approved JSON'}]},
        change_summary='initial approved version',
        generation_type=GenerationType.INITIAL,
        created_by=owner.id,
        is_current=True,
    )
    draft_version = ContentVersion(
        organization_id=org.id,
        content_item_id=draft_item.id,
        version_number=1,
        body_markdown='# Draft headline\n\nShould never export.',
        structured_json={'blocks': [{'type': 'paragraph', 'text': 'Draft JSON'}]},
        change_summary='draft version',
        generation_type=GenerationType.INITIAL,
        created_by=owner.id,
        is_current=True,
    )
    db.add_all([approved_version, draft_version])
    db.flush()
    approved_item.current_version_id = approved_version.id
    draft_item.current_version_id = draft_version.id

    db.add_all(
        [
            OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER),
            OrganizationMembership(organization_id=outsider_org.id, user_id=outsider.id, role=MembershipRole.CLIENT_OWNER),
        ]
    )
    db.commit()
    payload = {
        'owner': owner,
        'outsider': outsider,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'product_id': str(product.id),
        'content_plan_id': str(plan.id),
    }
    db.close()
    return payload


def test_manager_can_export_content_plan_to_markdown_and_download_only_approved_content(client, monkeypatch):
    fixture = seed_export_fixture()
    fake_storage = FakeStorageClient()
    monkeypatch.setattr(storage_module, 'get_storage_client', lambda _settings: fake_storage)

    create_response = client.post(
        f"/api/v1/content-plans/{fixture['content_plan_id']}/export",
        json={'format': 'markdown'},
        headers=auth_headers(client, fixture['owner'].email),
    )

    assert create_response.status_code == 201
    export_payload = create_response.json()
    assert export_payload['status'] == 'ready'
    assert export_payload['format'] == 'markdown'
    assert export_payload['content_plan_id'] == fixture['content_plan_id']
    assert export_payload['organization_id'] == fixture['organization_id']
    assert export_payload['brand_id'] == fixture['brand_id']
    assert export_payload['file_key'].startswith(
        f"organizations/{fixture['organization_id']}/brands/{fixture['brand_id']}/exports/"
    )

    listing_response = client.get(
        f"/api/v1/exports?organization_id={fixture['organization_id']}&brand_id={fixture['brand_id']}",
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert listing_response.status_code == 200
    assert listing_response.json()['items'][0]['id'] == export_payload['id']

    detail_response = client.get(
        f"/api/v1/exports/{export_payload['id']}",
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert detail_response.status_code == 200
    assert detail_response.json()['id'] == export_payload['id']

    download_response = client.get(
        f"/api/v1/exports/{export_payload['id']}/download",
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert download_response.status_code == 200
    assert download_response.headers['content-type'].startswith('text/markdown')
    assert '# Approved headline' in download_response.text
    assert 'Approved JSON' in download_response.text
    assert 'Draft headline' not in download_response.text
    assert 'Draft JSON' not in download_response.text

    forbidden_download = client.get(
        f"/api/v1/exports/{export_payload['id']}/download",
        headers=auth_headers(client, fixture['outsider'].email),
    )
    assert forbidden_download.status_code == 403


def test_manager_can_export_filtered_items_to_csv_and_zip(client, monkeypatch):
    fixture = seed_export_fixture()
    fake_storage = FakeStorageClient()
    monkeypatch.setattr(storage_module, 'get_storage_client', lambda _settings: fake_storage)

    csv_response = client.post(
        '/api/v1/exports',
        json={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'content_plan_id': fixture['content_plan_id'],
            'format': 'csv',
        },
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert csv_response.status_code == 201
    csv_export = csv_response.json()
    assert csv_export['status'] == 'ready'
    csv_download = client.get(
        f"/api/v1/exports/{csv_export['id']}/download",
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert csv_download.status_code == 200
    assert csv_download.headers['content-type'].startswith('text/csv')
    assert 'Approved item' in csv_download.text
    assert 'Draft item' not in csv_download.text

    zip_response = client.post(
        '/api/v1/exports',
        json={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'content_plan_id': fixture['content_plan_id'],
            'format': 'zip',
        },
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert zip_response.status_code == 201
    zip_export = zip_response.json()
    zip_download = client.get(
        f"/api/v1/exports/{zip_export['id']}/download",
        headers=auth_headers(client, fixture['owner'].email),
    )
    assert zip_download.status_code == 200
    assert zip_download.headers['content-type'].startswith('application/zip')

    archive = zipfile.ZipFile(io.BytesIO(zip_download.content))
    names = archive.namelist()
    assert 'content-items.csv' in names
    assert 'content-items.md' in names
    markdown_text = archive.read('content-items.md').decode()
    csv_text = archive.read('content-items.csv').decode()
    manifest = json.loads(archive.read('manifest.json').decode())

    assert '# Approved headline' in markdown_text
    assert 'Draft headline' not in markdown_text
    assert 'Approved item' in csv_text
    assert 'Draft item' not in csv_text
    assert manifest['approved_item_count'] == 1
    assert manifest['organization_id'] == fixture['organization_id']
    assert manifest['brand_id'] == fixture['brand_id']
