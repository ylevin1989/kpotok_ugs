from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ALPHA = 'worker-alpha'
WORKER_BETA = 'worker-beta'


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
    owner = seed_user('owner-p28@example.com')
    reviewer = seed_user('reviewer-p28@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet28', slug='uno-packet28', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p28')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief', content='Need a campaign launch plan.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    job = db.get(Brief, brief.id)
    created_job = None
    from app.db.models.job import Job
    created_job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Generate launch copy', status='queued')
    db.add(created_job)
    db.commit()
    db.refresh(created_job)
    db.close()
    return owner, reviewer, org, brand, brief, created_job


def test_claim_increments_attempt_count_and_complete_persists_output_text(client):
    _, _, _, _, _, job = seed_jobs_fixture()

    claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))
    assert claim.status_code == 200
    claimed = claim.json()
    assert claimed['id'] == str(job.id)
    assert claimed['attempt_count'] == 1
    assert claimed['output_text'] is None

    complete = client.post(
        f"/api/v1/jobs/{job.id}/complete",
        json={'output_text': 'stub-output-for-generate-launch-copy'},
        headers=worker_headers(WORKER_ALPHA),
    )
    assert complete.status_code == 200
    completed = complete.json()
    assert completed['status'] == 'completed'
    assert completed['attempt_count'] == 1
    assert completed['output_text'] == 'stub-output-for-generate-launch-copy'


def test_reclaim_increments_attempt_count_again(client):
    _, _, _, _, _, job = seed_jobs_fixture()

    first_claim = client.post(f'/api/v1/jobs/{job.id}/claim', headers=worker_headers(WORKER_ALPHA))
    assert first_claim.status_code == 200
    assert first_claim.json()['attempt_count'] == 1

    db = SessionLocal()
    from app.db.models.job import Job
    db_job = db.get(Job, job.id)
    from datetime import datetime, timedelta, timezone
    db_job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    db.close()

    reclaim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))
    assert reclaim.status_code == 200
    reclaimed = reclaim.json()
    assert reclaimed['id'] == str(job.id)
    assert reclaimed['worker_id'] == WORKER_BETA
    assert reclaimed['attempt_count'] == 2
