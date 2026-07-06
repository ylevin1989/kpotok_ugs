from datetime import datetime, timedelta, timezone

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_TOKEN = 'packet23-worker-token'
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
    return {'X-Worker-Token': WORKER_TOKEN, 'X-Worker-Id': worker_id}


def seed_jobs_fixture(stale_running: bool = False):
    owner = seed_user('owner-p25@example.com')
    reviewer = seed_user('reviewer-p25@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet25', slug='uno-packet25', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p25')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Lease brief', content='Need lease and recovery semantics.')
    db.add(brief)
    db.flush()

    if stale_running:
        job1 = Job(
            organization_id=org.id,
            brand_id=brand.id,
            brief_id=brief.id,
            title='Stale running job',
            status='running',
            worker_id=WORKER_ALPHA,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            lease_expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )
    else:
        job1 = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Queued job 1', status='queued')
    job2 = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Queued job 2', status='queued')
    db.add(job1)
    db.flush()
    db.add(job2)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(job1)
    db.refresh(job2)
    db.close()
    return owner, reviewer, org, brand, brief, job1, job2


def test_claim_sets_lease_expiry_and_heartbeat_extends_it(client):
    _, _, _, _, _, job1, _ = seed_jobs_fixture()

    claim_response = client.post(f'/api/v1/jobs/{job1.id}/claim', headers=worker_headers(WORKER_ALPHA))

    assert claim_response.status_code == 200
    claimed = claim_response.json()
    assert claimed['lease_expires_at'] is not None
    first_lease = claimed['lease_expires_at']

    heartbeat_response = client.post(f'/api/v1/jobs/{job1.id}/heartbeat', headers=worker_headers(WORKER_ALPHA))

    assert heartbeat_response.status_code == 200
    heartbeat = heartbeat_response.json()
    assert heartbeat['worker_id'] == WORKER_ALPHA
    assert heartbeat['lease_expires_at'] > first_lease


def test_claim_next_reclaims_stale_running_job_before_new_queued_job(client):
    _, _, _, _, _, job1, job2 = seed_jobs_fixture(stale_running=True)

    response = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))

    assert response.status_code == 200
    claimed = response.json()
    assert claimed['id'] == str(job1.id)
    assert claimed['status'] == 'running'
    assert claimed['worker_id'] == WORKER_BETA
    assert claimed['lease_expires_at'] is not None
    assert claimed['id'] != str(job2.id)


def test_stale_owner_cannot_complete_after_reclaim(client):
    _, _, _, _, _, job1, _ = seed_jobs_fixture(stale_running=True)

    reclaim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))
    assert reclaim.status_code == 200
    assert reclaim.json()['id'] == str(job1.id)

    response = client.post(f'/api/v1/jobs/{job1.id}/complete', headers=worker_headers(WORKER_ALPHA))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Job is owned by another worker'


def test_non_owner_cannot_heartbeat_foreign_running_job(client):
    _, _, _, _, _, job1, _ = seed_jobs_fixture()

    claim = client.post(f'/api/v1/jobs/{job1.id}/claim', headers=worker_headers(WORKER_ALPHA))
    assert claim.status_code == 200

    response = client.post(f'/api/v1/jobs/{job1.id}/heartbeat', headers=worker_headers(WORKER_BETA))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Job is owned by another worker'
