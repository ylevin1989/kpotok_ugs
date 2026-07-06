import time
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
    org = Organization(name='Uno Packet69', slug=f"uno-packet69-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 69', slug=f"rocket-tea-p69-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 69', content='Need a campaign launch plan 69.')
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


def test_execution_trace_exposes_progress_extrema_and_retry_profile(client):
    owner, job_id = seed_job_fixture('Packet 69 extrema and retry profile')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 55, 'progress_message': 'Expanded outline'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['progress_extrema'] == {
        'min_progress_percent': 25,
        'max_progress_percent': 80,
        'progress_spread_percent': 55,
        'first_progress_percent': 25,
    }
    assert trace['retry_profile'] == {
        'attempt_count': 1,
        'reclaim_count': 0,
        'latest_attempt_number': 1,
        'current_claim_type': 'claimed',
    }
    assert trace['attempt_summary']['progress_remaining_percent'] == 20
    assert trace['attempt_summary']['first_progress_percent'] == 25
    assert trace['attempt_summary']['max_progress_percent'] == 80


def test_terminal_events_carry_worker_recap_and_progress_span(client):
    owner, job_id = seed_job_fixture('Packet 69 worker recap and span')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={'output_text': 'done'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    completed_event = response.json()['execution_trace']['events'][-1]

    assert completed_event['worker_recap'] == {
        'current_worker_id': WORKER_ALPHA,
        'reclaimed_from_worker_id': None,
        'worker_count': 1,
        'retry_reason': None,
        'current_claim_type': 'claimed',
        'had_reclaim': False,
        'reclaim_count': 0,
        'attempt_count': 1,
        'latest_transition_tag': None,
        'latest_worker_metadata_keys': [],
        'worker_metadata_key_count': 0,
    }
    assert completed_event['timeline_digest']['progress_span_percent'] == 55


def test_reclaim_updates_worker_history_and_compact_reclaim_count(client):
    owner, job_id = seed_job_fixture('Packet 69 worker history and reclaim count')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 35, 'progress_message': 'First attempt progress'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    db = SessionLocal()
    from app.db.models.job import Job
    db_job = db.get(Job, UUID(job_id))
    db_job.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=5)
    db.commit()
    db.close()

    assert client.post('/api/v1/jobs/claim-next', headers=worker_headers(WORKER_BETA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 15, 'progress_message': 'Retry started'},
        headers=worker_headers(WORKER_BETA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['worker_history'] == [WORKER_ALPHA, WORKER_BETA]
    assert trace['retry_profile'] == {
        'attempt_count': 2,
        'reclaim_count': 1,
        'latest_attempt_number': 2,
        'current_claim_type': 'reclaimed',
    }
    assert trace['trace_compact_summary']['reclaim_count'] == 1


def test_failed_events_carry_retry_context(client):
    owner, job_id = seed_job_fixture('Packet 69 failure retry context')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    failed_event = response.json()['execution_trace']['events'][-1]

    assert failed_event['failure_digest']['retry_reason'] is None
    assert failed_event['worker_recap']['worker_count'] == 1
