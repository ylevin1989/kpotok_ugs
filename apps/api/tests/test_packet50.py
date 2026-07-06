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
    org = Organization(name='Uno Packet50', slug=f"uno-packet50-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 50', slug=f"rocket-tea-p50-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 50', content='Need a campaign launch plan 50.')
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


def test_execution_trace_exposes_attempt_summary_and_progress_deltas(client):
    owner, job_id = seed_job_fixture('Packet 50 attempt summary and deltas')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'progress_percent': 25,
            'progress_message': 'Started draft',
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'progress_percent': 55,
            'progress_message': 'Expanded outline',
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    first_heartbeat = trace['events'][1]
    second_heartbeat = trace['events'][2]

    assert first_heartbeat['progress_delta_percent'] == 25
    assert second_heartbeat['progress_delta_percent'] == 30
    assert trace['attempt_summary'] == {
        'attempt_number': 1,
        'progress_event_count': 2,
        'last_stage_name': 'generate-copy',
        'last_stage_label': None,
        'last_progress_percent': 55,
        'last_progress_sequence': 2,
        'attempt_duration_seconds': trace['attempt_summary']['attempt_duration_seconds'],
        'progress_velocity_percent_per_second': trace['attempt_summary']['progress_velocity_percent_per_second'],
        'attempt_completion_ratio': 0.55,
        'last_stage_repeat_count': 2,
        'attempt_event_density_per_second': trace['attempt_summary']['attempt_event_density_per_second'],
        'progress_remaining_percent': 45,
        'first_progress_percent': 25,
        'first_stage_label': None,
        'first_transition_tag': None,
        'min_progress_percent': 25,
        'max_progress_percent': 55,
        'unique_stage_count': 1,
        'unique_transition_tag_count': 0,
        'worker_metadata_key_count': 0,
        'transition_tag_total_count': 0,
        'latest_worker_metadata_keys': [],
        'latest_transition_tag': None,
        'progress_sequence_span': 2,
        'total_progress_delta_percent': 30,
        'average_progress_delta_percent': 27.5,
        'average_progress_percent': 40.0,
    }
    assert trace['attempt_summary']['attempt_duration_seconds'] >= 0.0
    assert trace['attempt_summary']['progress_velocity_percent_per_second'] > 0
    assert trace['attempt_summary']['attempt_event_density_per_second'] > 0


def test_terminal_events_carry_attempt_snapshot(client):
    owner, job_id = seed_job_fixture('Packet 50 terminal attempt snapshot')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'persist-artifact',
            'progress_percent': 80,
            'progress_message': 'Uploading artifact',
        },
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'Hermes upstream timeout'},
        headers=worker_headers(WORKER_ALPHA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']
    failed_event = trace['events'][-1]

    assert failed_event['attempt_snapshot'] == {
        'attempt_number': 1,
        'progress_event_count': 1,
        'last_stage_name': 'persist-artifact',
        'last_stage_label': None,
        'last_progress_percent': 80,
        'last_progress_sequence': 1,
        'attempt_duration_seconds': failed_event['attempt_snapshot']['attempt_duration_seconds'],
        'progress_velocity_percent_per_second': failed_event['attempt_snapshot']['progress_velocity_percent_per_second'],
        'attempt_completion_ratio': 0.8,
        'last_stage_repeat_count': 1,
        'attempt_event_density_per_second': failed_event['attempt_snapshot']['attempt_event_density_per_second'],
        'progress_remaining_percent': 20,
        'first_progress_percent': 80,
        'first_stage_label': None,
        'first_transition_tag': None,
        'min_progress_percent': 80,
        'max_progress_percent': 80,
        'unique_stage_count': 1,
        'unique_transition_tag_count': 0,
        'worker_metadata_key_count': 0,
        'transition_tag_total_count': 0,
        'latest_worker_metadata_keys': [],
        'latest_transition_tag': None,
        'progress_sequence_span': 1,
        'total_progress_delta_percent': 0,
        'average_progress_delta_percent': 80.0,
        'average_progress_percent': 80.0,
    }
    assert failed_event['attempt_snapshot']['attempt_duration_seconds'] >= 0.0
    assert failed_event['attempt_snapshot']['progress_velocity_percent_per_second'] > 0
    assert failed_event['attempt_snapshot']['attempt_event_density_per_second'] > 0


def test_reclaim_resets_attempt_summary_for_new_attempt(client):
    owner, job_id = seed_job_fixture('Packet 50 reclaim resets attempt summary')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers(WORKER_ALPHA)).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/heartbeat',
        json={
            'stage_name': 'generate-copy',
            'progress_percent': 35,
            'progress_message': 'First attempt progress',
        },
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
        json={
            'stage_name': 'generate-copy',
            'progress_percent': 15,
            'progress_message': 'Retry started',
        },
        headers=worker_headers(WORKER_BETA),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['attempt_summary'] == {
        'attempt_number': 2,
        'progress_event_count': 1,
        'last_stage_name': 'generate-copy',
        'last_stage_label': None,
        'last_progress_percent': 15,
        'last_progress_sequence': 1,
        'attempt_duration_seconds': trace['attempt_summary']['attempt_duration_seconds'],
        'progress_velocity_percent_per_second': trace['attempt_summary']['progress_velocity_percent_per_second'],
        'attempt_completion_ratio': 0.15,
        'last_stage_repeat_count': 1,
        'attempt_event_density_per_second': trace['attempt_summary']['attempt_event_density_per_second'],
        'progress_remaining_percent': 85,
        'first_progress_percent': 15,
        'first_stage_label': None,
        'first_transition_tag': None,
        'min_progress_percent': 15,
        'max_progress_percent': 15,
        'unique_stage_count': 1,
        'unique_transition_tag_count': 0,
        'worker_metadata_key_count': 0,
        'transition_tag_total_count': 0,
        'latest_worker_metadata_keys': [],
        'latest_transition_tag': None,
        'progress_sequence_span': 1,
        'total_progress_delta_percent': 0,
        'average_progress_delta_percent': 15.0,
        'average_progress_percent': 15.0,
    }
    assert trace['attempt_summary']['attempt_duration_seconds'] >= 0.0
    assert trace['attempt_summary']['progress_velocity_percent_per_second'] > 0
    assert trace['attempt_summary']['attempt_event_density_per_second'] > 0
