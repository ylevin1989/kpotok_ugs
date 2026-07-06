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
    org = Organization(name='Uno Packet79', slug=f"uno-packet79-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 79', slug=f"rocket-tea-p79-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 79', content='Need a campaign launch plan 79.')
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


def test_execution_trace_exposes_transition_and_metadata_rollups(client):
    owner, job_id = seed_job_fixture('Packet 79 transition and metadata rollups')

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
            'stage_name': 'persist-artifact',
            'stage_label': 'Upload',
            'progress_percent': 80,
            'progress_message': 'Uploading artifact',
            'transition_tag': 'artifact-upload',
            'worker_metadata': {'model': 'gpt-test', 'queue': 'fast'},
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['transition_tag_rollup'] == ['draft-start', 'artifact-upload']
    assert trace['worker_metadata_key_summary'] == ['model', 'queue', 'region']
    assert trace['stage_label_summary'] == {
        'generate-copy': 'Drafting',
        'persist-artifact': 'Upload',
    }
    assert trace['attempt_summary']['progress_sequence_span'] == 2
    assert trace['attempt_summary']['total_progress_delta_percent'] == 55


def test_terminal_completed_event_carries_progress_window_and_timeline_first_stage(client):
    owner, job_id = seed_job_fixture('Packet 79 terminal progress window')

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
    trace = response.json()['execution_trace']
    completed_event = trace['events'][-1]

    assert trace['trace_compact_summary']['has_progress'] is True
    assert completed_event['timeline_digest']['first_stage_name'] == 'generate-copy'
    assert completed_event['progress_window'] == {
        'first_progress_percent': 25,
        'last_progress_percent': 80,
        'min_progress_percent': 25,
        'max_progress_percent': 80,
        'progress_remaining_percent': 20,
        'average_progress_percent': 52.5,
        'total_progress_delta_percent': 55,
        'progress_span_percent': 55,
        'progress_sequence_span': 2,
    }


def test_reclaim_exposes_current_claim_type_and_worker_retry_reason(client):
    owner, job_id = seed_job_fixture('Packet 79 reclaim worker retry reason')

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
    trace = response.json()['execution_trace']
    failed_event = trace['events'][-1]

    assert trace['retry_profile']['current_claim_type'] == 'reclaimed'
    assert failed_event['worker_recap']['retry_reason'] == 'lease_expired'
