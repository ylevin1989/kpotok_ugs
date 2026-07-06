from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


WORKER_TOKEN = 'packet23-worker-token'


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


def worker_headers() -> dict[str, str]:
    return {'X-Worker-Token': WORKER_TOKEN}


def seed_job_fixture():
    owner = seed_user('owner-p23@example.com')
    reviewer = seed_user('reviewer-p23@example.com')
    outsider = seed_user('outsider-p23@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet23', slug='uno-packet23', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p23')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief', content='Need a campaign launch plan.')
    db.add(brief)
    db.flush()
    job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title='Generate landing page copy', status='queued')
    db.add(job)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(brief)
    db.refresh(job)
    db.close()
    return owner, reviewer, outsider, org, brand, brief, job


def test_worker_can_claim_job_and_reviewer_sees_running_status(client):
    _, reviewer, _, _, _, _, job = seed_job_fixture()

    response = client.post(f'/api/v1/jobs/{job.id}/claim', headers=worker_headers())

    assert response.status_code == 200
    claimed = response.json()
    assert claimed['status'] == 'running'
    assert claimed['started_at'] is not None
    assert claimed['finished_at'] is None
    assert claimed['error_message'] is None

    get_response = client.get(f'/api/v1/jobs/{job.id}', headers=auth_headers(client, reviewer.email))
    assert get_response.status_code == 200
    assert get_response.json()['status'] == 'running'


def test_worker_can_complete_running_job(client):
    _, _, _, _, _, _, job = seed_job_fixture()

    claim_response = client.post(f'/api/v1/jobs/{job.id}/claim', headers=worker_headers())
    assert claim_response.status_code == 200

    response = client.post(f'/api/v1/jobs/{job.id}/complete', headers=worker_headers())

    assert response.status_code == 200
    completed = response.json()
    assert completed['status'] == 'completed'
    assert completed['started_at'] is not None
    assert completed['finished_at'] is not None
    assert completed['error_message'] is None


def test_worker_can_fail_running_job_with_error_message(client):
    _, _, _, _, _, _, job = seed_job_fixture()

    claim_response = client.post(f'/api/v1/jobs/{job.id}/claim', headers=worker_headers())
    assert claim_response.status_code == 200

    response = client.post(
        f'/api/v1/jobs/{job.id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(),
    )

    assert response.status_code == 200
    failed = response.json()
    assert failed['status'] == 'failed'
    assert failed['started_at'] is not None
    assert failed['finished_at'] is not None
    assert failed['error_message'] == 'Hermes upstream timeout'


def test_non_worker_cannot_call_job_lifecycle_hooks(client):
    owner, _, _, _, _, _, job = seed_job_fixture()

    response = client.post(f'/api/v1/jobs/{job.id}/claim', headers=auth_headers(client, owner.email))

    assert response.status_code == 401
    assert response.json()['detail'] == 'Invalid worker token'
