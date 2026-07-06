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
    org = Organization(name='Uno Packet89', slug=f"uno-packet89-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 89', slug=f"rocket-tea-p89-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 89', content='Need a campaign launch plan 89.')
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


def test_execution_trace_exposes_transition_counts_and_label_history(client):
    owner, job_id = seed_job_fixture('Packet 89 transition counts and label history')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'stage_label': 'Drafting',
            'progress_percent': 25,
            'progress_message': 'Started draft',
            'transition_tag': 'draft-start',
            'worker_metadata': {'model': 'gpt-test', 'region': 'eu'},
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'stage_label': 'Drafting refined',
            'progress_percent': 55,
            'progress_message': 'Expanded outline',
            'transition_tag': 'draft-start',
            'worker_metadata': {'model': 'gpt-test', 'queue': 'fast'},
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'persist-artifact',
            'stage_label': 'Upload',
            'progress_percent': 80,
            'progress_message': 'Uploading artifact',
            'transition_tag': 'artifact-upload',
            'worker_metadata': {'model': 'gpt-test', 'queue': 'fast', 'region': 'eu'},
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['transition_tag_counts'] == {'draft-start': 2, 'artifact-upload': 1}
    assert trace['latest_worker_metadata'] == {'model': 'gpt-test', 'queue': 'fast', 'region': 'eu'}
    assert trace['stage_label_history'] == {
        'generate-copy': ['Drafting', 'Drafting refined'],
        'persist-artifact': ['Upload'],
    }
    assert trace['attempt_summary']['average_progress_delta_percent'] == 26.666666666666668
    assert trace['attempt_summary']['last_stage_label'] == 'Upload'


def test_terminal_completed_event_carries_progress_total_delta_and_last_sequence(client):
    owner, job_id = seed_job_fixture('Packet 89 terminal digests')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'stage_label': 'Drafting', 'progress_percent': 25, 'progress_message': 'Started draft'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'stage_label': 'Upload', 'progress_percent': 80, 'progress_message': 'Uploading artifact'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={'output_text': 'done'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    completed_event = trace['events'][-1]

    assert trace['trace_compact_summary']['progress_span_percent'] == 55
    assert completed_event['timeline_digest']['last_progress_sequence'] == 2
    assert completed_event['progress_digest']['total_progress_delta_percent'] == 55


def test_reclaim_exposes_claim_type_recap_and_failure_remaining_percent(client):
    owner, job_id = seed_job_fixture('Packet 89 reclaim claim-type recap')

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
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(WORKER_BETA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    failed_event = response.json()['execution_trace']['events'][-1]

    assert failed_event['worker_recap']['current_claim_type'] == 'reclaimed'
    assert failed_event['failure_digest']['progress_remaining_percent'] == 85
