from datetime import datetime, timedelta, timezone
from uuid import UUID

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ALPHA = 'worker-alpha'
WORKER_BETA = 'worker-beta'


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


def worker_headers(worker_id: str) -> dict[str, str]:
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': worker_id}


def seed_job_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet41', slug=f"uno-packet41-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 41', slug=f"rocket-tea-p41-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 41', content='Need a campaign launch plan 41.')
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


def test_execution_trace_heartbeat_event_includes_progress_and_worker_metadata(client):
    owner, job_id = seed_job_fixture('Packet 41 heartbeat progress metadata')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'stage_label': 'Generate copy',
            'progress_percent': 45,
            'progress_message': 'Drafting variant B',
            'worker_metadata': {
                'model': 'hermes-sonnet',
                'attempt_token': 'tok-41',
                'items_completed': 9,
            },
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    heartbeat_event = trace['events'][-1]

    assert heartbeat_event['event'] == 'heartbeat'
    assert heartbeat_event['stage_name'] == 'generate-copy'
    assert heartbeat_event['stage_label'] == 'Generate copy'
    assert heartbeat_event['progress_percent'] == 45
    assert heartbeat_event['progress_message'] == 'Drafting variant B'
    assert heartbeat_event['worker_metadata'] == {
        'model': 'hermes-sonnet',
        'attempt_token': 'tok-41',
        'items_completed': 9,
    }


def test_claim_next_reclaim_emits_reclaimed_attempt_trace_event(client):
    owner, job_id = seed_job_fixture('Packet 41 reclaim trace details')

    first_claim = client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA))
    assert first_claim.status_code == 200

    db = SessionLocal()
    from app.db.models.job import Job
    db_job = db.get(Job, UUID(job_id))
    db_job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    db.close()

    reclaim = client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA))
    assert reclaim.status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    claimed_event = trace['events'][0]

    assert claimed_event['event'] == 'claimed'
    assert claimed_event['worker_id'] == WORKER_BETA
    assert claimed_event['claim_type'] == 'reclaimed'
    assert claimed_event['attempt_number'] == 2
    assert claimed_event['reclaimed_from_worker_id'] == WORKER_ALPHA
    assert trace['stage_history'] == ['claimed']
