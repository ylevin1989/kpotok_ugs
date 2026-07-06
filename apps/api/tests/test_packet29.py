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
    owner = seed_user('owner-p29@example.com')
    reviewer = seed_user('reviewer-p29@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet29', slug='uno-packet29', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 29', slug='rocket-tea-p29')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 29', content='Need a campaign launch plan 29.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    from app.db.models.job import Job
    job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Generate observable launch copy', status='queued')
    db.add(job)
    db.commit()
    db.refresh(job)
    db.close()
    return owner, reviewer, org, brand, brief, job


def test_claim_heartbeat_and_complete_expose_stage_observability(client):
    _, _, _, _, _, job = seed_jobs_fixture()

    claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))
    assert claim.status_code == 200
    claimed = claim.json()
    assert claimed['id'] == str(job.id)
    assert claimed['last_stage'] == 'claimed'
    assert claimed['last_heartbeat_at'] is not None

    heartbeat = client.post(
        f'/api/v1/jobs/{job.id}/heartbeat',
        json={'stage_name': 'render-output'},
        headers=worker_headers(WORKER_ALPHA),
    )
    assert heartbeat.status_code == 200
    heartbeated = heartbeat.json()
    assert heartbeated['last_stage'] == 'render-output'
    assert heartbeated['last_heartbeat_at'] is not None

    complete = client.post(
        f'/api/v1/jobs/{job.id}/complete',
        json={'output_text': 'observable-output'},
        headers=worker_headers(WORKER_ALPHA),
    )
    assert complete.status_code == 200
    completed = complete.json()
    assert completed['status'] == 'completed'
    assert completed['last_stage'] == 'completed'
    assert completed['last_heartbeat_at'] is not None
    assert completed['output_text'] == 'observable-output'
