from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


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


def worker_headers() -> dict[str, str]:
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': 'packet40-worker'}


def seed_job_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet40', slug=f"uno-packet40-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 40', slug=f"rocket-tea-p40-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 40', content='Need a campaign launch plan 40.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title=title, status='queued')
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = str(job.id)
    db.close()
    return owner, job_id


def test_execution_trace_failed_event_classifies_artifact_scope_rejection(client):
    owner, job_id = seed_job_fixture('Packet 40 artifact scope failure')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers()).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact'},
        headers=worker_headers(),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'processing error: artifact key escaped job scope'},
        headers=worker_headers(),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    failed_event = trace['events'][-1]

    assert trace['failure_stage'] == 'persist-artifact'
    assert trace['failure_code'] == 'artifact_scope_rejection'
    assert failed_event['failure_stage'] == 'persist-artifact'
    assert failed_event['failure_code'] == 'artifact_scope_rejection'


def test_execution_trace_failed_event_classifies_upstream_timeout(client):
    owner, job_id = seed_job_fixture('Packet 40 upstream timeout failure')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers()).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy'},
        headers=worker_headers(),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    failed_event = trace['events'][-1]

    assert trace['failure_stage'] == 'generate-copy'
    assert trace['failure_code'] == 'upstream_timeout'
    assert failed_event['failure_stage'] == 'generate-copy'
    assert failed_event['failure_code'] == 'upstream_timeout'
