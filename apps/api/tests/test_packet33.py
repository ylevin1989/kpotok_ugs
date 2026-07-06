from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal
import app.api.v1.jobs as jobs_module


def seed_user(email: str, password: str = 'test12345', full_name: str | None = None) -> User:
    db = SessionLocal()
    user = User(
        email=email,
        full_name=full_name or email.split('@')[0].title(),
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_artifact_job_fixture():
    owner = seed_user('owner-p33@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet33', slug='uno-packet33', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 33', slug='rocket-tea-p33')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 33', content='Need a campaign launch plan 33.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title='Read artifact content',
        status='completed',
        output_artifact_key='jobs/generated-read-artifact-content.txt',
        output_artifact_url='s3://content-factory/jobs/generated-read-artifact-content.txt',
        output_artifact_content_type='text/plain',
        output_artifact_size_bytes=19,
        output_artifact_etag='etag-packet33',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.close()
    return owner, org, brand, brief, job


def test_get_artifact_returns_text_payload_for_authorized_user(client, monkeypatch):
    owner, _, _, _, job = seed_artifact_job_fixture()

    def fake_read_job_artifact(_settings, _job):
        return b'packet33-artifact\n', 'text/plain'

    monkeypatch.setattr(jobs_module, 'read_job_artifact', fake_read_job_artifact, raising=False)

    response = client.get(f'/api/v1/jobs/{job.id}/artifact', headers=auth_headers(client, owner.email))

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('text/plain')
    assert response.content == b'packet33-artifact\n'


def test_get_artifact_rejects_job_without_persisted_artifact(client):
    owner = seed_user('owner-p33-no-artifact@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet33 No Artifact', slug='uno-packet33-no-artifact', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 33 No Artifact', slug='rocket-tea-p33-no-artifact')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 33 no artifact', content='No artifact yet.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title='No artifact job',
        status='completed',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    db.close()

    response = client.get(f'/api/v1/jobs/{job.id}/artifact', headers=auth_headers(client, owner.email))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Job artifact is not available'
