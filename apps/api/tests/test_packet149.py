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
    org = Organization(name='Uno Packet149', slug=f"uno-packet149-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 149', slug=f"rocket-tea-p149-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 149', content='Need a campaign launch plan 149.')
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


def test_execution_trace_exposes_total_tags_and_latest_metadata_carry_forward(client):
    owner, job_id = seed_job_fixture('Packet 149 total tags and latest metadata carry forward')

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

    assert trace['attempt_summary']['transition_tag_total_count'] == 2
    assert trace['attempt_summary']['latest_worker_metadata_keys'] == ['model', 'queue', 'region']
    assert trace['trace_compact_summary']['first_transition_tag'] == 'draft-start'
    assert trace['trace_compact_summary']['first_progress_percent'] == 25
    assert trace['trace_compact_summary']['max_progress_percent'] == 80


def test_terminal_completed_event_carries_tag_and_metadata_breadth_recaps(client):
    owner, job_id = seed_job_fixture('Packet 149 terminal tag and metadata breadth recaps')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'generate-copy', 'stage_label': 'Drafting', 'progress_percent': 25, 'progress_message': 'Started draft', 'transition_tag': 'draft-start', 'worker_metadata': {'model': 'gpt-test', 'queue': 'fast'}},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={'stage_name': 'persist-artifact', 'stage_label': 'Upload', 'progress_percent': 80, 'progress_message': 'Uploading artifact', 'transition_tag': 'artifact-upload', 'worker_metadata': {'model': 'gpt-test', 'queue': 'fast', 'region': 'eu'}},
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

    assert completed_event['timeline_digest']['worker_metadata_key_count'] == 3
    assert completed_event['progress_digest']['latest_transition_tag'] == 'artifact-upload'
    assert completed_event['progress_digest']['worker_metadata_key_count'] == 3
    assert completed_event['worker_recap']['worker_metadata_key_count'] == 3


def test_reclaim_failed_event_carries_latest_metadata_and_tag_totals(client):
    owner, job_id = seed_job_fixture('Packet 149 reclaim latest metadata and tag totals')

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
        json={'stage_name': 'persist-artifact', 'progress_percent': 15, 'progress_message': 'Retry started', 'transition_tag': 'artifact-retry', 'worker_metadata': {'model': 'gpt-test', 'region': 'eu'}},
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

    assert failed_event['failure_digest']['latest_worker_metadata_keys'] == ['model', 'region']
    assert failed_event['failure_digest']['transition_tag_total_count'] == 1
