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


def seed_jobs_fixture():
    owner = seed_user('owner-p24@example.com')
    reviewer = seed_user('reviewer-p24@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet24', slug='uno-packet24', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p24')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Queue brief', content='Need queue ownership semantics.')
    db.add(brief)
    db.flush()
    job1 = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Oldest queued job', status='queued')
    job2 = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Second queued job', status='queued')
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


def test_worker_can_claim_next_oldest_queued_job_and_sets_worker_id(client):
    _, reviewer, _, _, _, job1, job2 = seed_jobs_fixture()

    response = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))

    assert response.status_code == 200
    claimed = response.json()
    assert claimed['id'] == str(job1.id)
    assert claimed['status'] == 'running'
    assert claimed['worker_id'] == WORKER_ALPHA
    assert claimed['started_at'] is not None

    list_response = client.get(
        f'/api/v1/jobs?organization_id={job1.organization_id}&brand_id={job1.brand_id}&brief_id={job1.brief_id}',
        headers={'Authorization': f'Bearer {client.post("/api/v1/auth/login", json={"email": reviewer.email, "password": "test12345"}).json()["access_token"]}'},
    )
    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert items[0]['id'] == str(job1.id)
    assert items[0]['worker_id'] == WORKER_ALPHA
    assert items[1]['id'] == str(job2.id)
    assert items[1]['status'] == 'queued'


def test_second_worker_claim_next_skips_running_job_and_claims_next_queued_job(client):
    _, _, _, _, _, job1, job2 = seed_jobs_fixture()

    first_claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))
    assert first_claim.status_code == 200

    second_claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))

    assert second_claim.status_code == 200
    claimed = second_claim.json()
    assert claimed['id'] == str(job2.id)
    assert claimed['worker_id'] == WORKER_BETA
    assert claimed['status'] == 'running'


def test_worker_cannot_complete_job_owned_by_another_worker(client):
    _, _, _, _, _, job1, _ = seed_jobs_fixture()

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == str(job1.id)

    response = client.post(f'/api/v1/jobs/{job1.id}/complete', headers=worker_headers(WORKER_BETA))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Job is owned by another worker'


def test_claim_next_returns_not_found_when_no_queued_jobs_remain(client):
    _, _, _, _, _, _, _ = seed_jobs_fixture()

    first_claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_ALPHA))
    assert first_claim.status_code == 200
    second_claim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))
    assert second_claim.status_code == 200

    response = client.post('/api/v1/jobs/claim-next', headers=worker_headers('worker-gamma'))

    assert response.status_code == 204
    assert response.content == b''
