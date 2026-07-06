from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ALPHA = 'worker-alpha'


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


def worker_headers(worker_id: str) -> dict[str, str]:
    return {
        'X-Worker-Token': settings.worker_token,
        'X-Worker-Id': worker_id,
    }


def seed_jobs_fixture():
    owner = seed_user('owner-p32@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet32', slug='uno-packet32', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 32', slug='rocket-tea-p32')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 32', content='Need a campaign launch plan 32.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Generate metadata launch copy', status='queued')
    db.add(job)
    db.commit()
    db.refresh(job)
    org_id = str(org.id)
    brand_id = str(brand.id)
    db.close()
    return owner, org_id, brand_id, brief, job


def test_complete_persists_artifact_metadata_and_public_readback(client):
    _, org_id, brand_id, _, job = seed_jobs_fixture()

    claim = client.post(f'/api/v1/jobs/{job.id}/claim', headers=worker_headers(WORKER_ALPHA))
    assert claim.status_code == 200

    expected_key = f'organizations/{org_id}/brands/{brand_id}/jobs/{job.id}/artifacts/result.txt'

    complete = client.post(
        f'/api/v1/jobs/{job.id}/complete',
        json={
            'output_text': 'metadata-output',
            'output_artifact_key': expected_key,
            'output_artifact_url': f's3://cf-artifacts/{expected_key}',
            'output_artifact_content_type': 'text/plain',
            'output_artifact_size_bytes': 57,
            'output_artifact_etag': 'etag-packet32',
        },
        headers=worker_headers(WORKER_ALPHA),
    )
    assert complete.status_code == 200
    completed = complete.json()
    assert completed['status'] == 'completed'
    assert completed['output_text'] == 'metadata-output'
    assert completed['output_artifact_key'] == expected_key
    assert completed['output_artifact_url'] == f's3://cf-artifacts/{expected_key}'
    assert completed['output_artifact_content_type'] == 'text/plain'
    assert completed['output_artifact_size_bytes'] == 57
    assert completed['output_artifact_etag'] == 'etag-packet32'
