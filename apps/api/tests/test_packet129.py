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
    org = Organization(name='Uno Packet129', slug=f"uno-packet129-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 129', slug=f"rocket-tea-p129-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 129', content='Need a campaign launch plan 129.')
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


def test_execution_trace_exposes_label_tag_and_metadata_carry_forward(client):
    owner, job_id = seed_job_fixture('Packet 129 label tag and metadata carry forward')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'stage_label': 'Drafting',
            'progress_percent': 25,
            'progress_message': 'Started draft',
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

    assert trace['attempt_summary']['first_stage_label'] == 'Drafting'
    assert trace['attempt_summary']['latest_transition_tag'] == 'artifact-upload'
    assert trace['trace_compact_summary']['worker_metadata_key_count'] == 3
    assert trace['trace_compact_summary']['stage_label_entry_count'] == 2
    assert trace['trace_compact_summary']['latest_transition_tag'] == 'artifact-upload'


def test_terminal_completed_event_carries_tag_and_delta_recaps(client):
    owner, job_id = seed_job_fixture('Packet 129 terminal tag and delta recaps')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'stage_label': 'Drafting', 'progress_percent': 25, 'progress_message': 'Started draft', 'transition_tag': 'draft-start'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'stage_label': 'Upload', 'progress_percent': 80, 'progress_message': 'Uploading artifact', 'transition_tag': 'artifact-upload'},
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

    assert completed_event['timeline_digest']['latest_transition_tag'] == 'artifact-upload'
    assert completed_event['progress_digest']['max_progress_percent'] == 80
    assert completed_event['progress_digest']['unique_transition_tag_count'] == 2
    assert completed_event['progress_window']['total_progress_delta_percent'] == 55


def test_reclaim_failed_event_carries_latest_tag_context(client):
    owner, job_id = seed_job_fixture('Packet 129 reclaim latest tag context')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'progress_percent': 35, 'progress_message': 'First attempt progress', 'transition_tag': 'draft-start'},
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
        json={'stage_name': 'persist-artifact', 'progress_percent': 15, 'progress_message': 'Retry started', 'transition_tag': 'artifact-retry'},
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

    assert failed_event['failure_digest']['latest_transition_tag'] == 'artifact-retry'
    assert failed_event['worker_recap']['latest_transition_tag'] == 'artifact-retry'
