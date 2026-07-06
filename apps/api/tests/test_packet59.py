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
    org = Organization(name='Uno Packet59', slug=f"uno-packet59-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 59', slug=f"rocket-tea-p59-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 59', content='Need a campaign launch plan 59.')
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


def test_execution_trace_exposes_duration_ranking_and_attempt_ratios(client):
    owner, job_id = seed_job_fixture('Packet 59 duration ranking and ratios')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    time.sleep(0.03)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.02)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 55, 'progress_message': 'Expanded outline'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.02)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.01)
    assert client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={'output_text': 'done'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    ranking = trace['stage_duration_ranking']

    assert ranking[0]['stage_name'] == 'generate-copy'
    assert ranking[0]['total_duration_seconds'] >= ranking[1]['total_duration_seconds']
    assert ranking[0]['transition_count'] == 2
    assert ranking[0]['average_duration_seconds'] > 0
    assert trace['attempt_summary']['attempt_completion_ratio'] == 0.8
    assert trace['attempt_summary']['last_stage_repeat_count'] == 1
    assert trace['attempt_summary']['attempt_event_density_per_second'] > 0
    assert trace['trace_compact_summary']['current_stage'] == 'completed'
    assert trace['trace_compact_summary']['dominant_stage_name'] == 'generate-copy'


def test_terminal_events_carry_timeline_digest_and_scope_recap(client):
    owner, job_id = seed_job_fixture('Packet 59 terminal timeline digest')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    time.sleep(0.03)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.02)
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

    assert completed_event['timeline_digest']['stage_count'] == 4
    assert completed_event['timeline_digest']['heartbeat_count'] == 2
    assert completed_event['timeline_digest']['latest_stage_name'] == 'persist-artifact'
    assert completed_event['scope_recap']['organization_id']
    assert completed_event['scope_recap']['brand_id']
    assert completed_event['scope_recap']['brief_id']


def test_failed_events_carry_failure_digest_and_heartbeat_cadence(client):
    owner, job_id = seed_job_fixture('Packet 59 failure digest and cadence')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    time.sleep(0.03)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.02)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    time.sleep(0.02)
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    failed_event = trace['events'][-1]

    cadence = trace['heartbeat_cadence_summary']
    assert cadence['heartbeat_count'] == 2
    assert cadence['average_gap_seconds'] > 0
    assert cadence['max_gap_seconds'] >= cadence['average_gap_seconds']
    assert failed_event['failure_digest'] == {
        'failure_code': 'upstream_timeout',
        'failure_stage': 'persist-artifact',
        'had_progress': True,
        'attempt_number': 1,
        'retry_reason': None,
        'progress_remaining_percent': 20,
        'current_claim_type': 'claimed',
        'had_reclaim': False,
        'reclaim_count': 0,
        'worker_count': 1,
        'latest_transition_tag': None,
        'latest_worker_metadata_keys': [],
        'transition_tag_total_count': 0,
        'attempt_completion_ratio': 0.8,
    }


def test_reclaim_exposes_continuity_summary(client):
    owner, job_id = seed_job_fixture('Packet 59 reclaim continuity')

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
    time.sleep(0.03)
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'progress_percent': 15, 'progress_message': 'Retry started'},
        headers=worker_headers(WORKER_BETA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['reclaim_continuity'] == {
        'claim_type': 'reclaimed',
        'reclaimed_from_worker_id': WORKER_ALPHA,
        'retry_reason': 'lease_expired',
        'attempt_number': 2,
    }
    assert trace['attempt_summary']['attempt_number'] == 2
    assert trace['dominant_stage_name'] == 'persist-artifact'
    assert trace['attempt_summary']['attempt_completion_ratio'] == 0.15
