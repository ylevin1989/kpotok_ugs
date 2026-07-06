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
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': 'packet38-worker'}


def seed_job_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet38', slug=f"uno-packet38-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 38', slug=f"rocket-tea-p38-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 38', content='Need a campaign launch plan 38.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(organization_id=org.id, brand_id=brand.id, brief_id=brief.id, title=title, status='queued')
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = str(job.id)
    org_id = str(org.id)
    brand_id = str(brand.id)
    db.close()
    return owner, job_id, org_id, brand_id


def test_execution_trace_completed_event_includes_artifact_snapshot_and_lifecycle_metrics(client):
    owner, job_id, org_id, brand_id = seed_job_fixture('Packet 38 completed details')
    expected_key = f'organizations/{org_id}/brands/{brand_id}/jobs/{job_id}/artifacts/result.txt'

    claim = client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers())
    assert claim.status_code == 200
    heartbeat = client.post(f'/api/v1/jobs/{job_id}/heartbeat', json={'stage_name': 'render-output'}, headers=worker_headers())
    assert heartbeat.status_code == 200
    complete = client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={
            'output_text': 'packet38-result',
            'output_artifact_key': expected_key,
            'output_artifact_url': f's3://content-factory/{expected_key}',
            'output_artifact_content_type': 'text/plain',
            'output_artifact_size_bytes': 58,
            'output_artifact_etag': 'etag-packet38',
        },
        headers=worker_headers(),
    )
    assert complete.status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    completed_event = trace['events'][2]
    assert completed_event['event'] == 'completed'
    assert completed_event['worker_id'] == 'packet38-worker'
    assert completed_event['artifact_scope_status'] == 'validated'
    assert completed_event['lifecycle_seconds'] >= 0
    assert completed_event['stage_count'] == 3
    assert completed_event['artifact'] == {
        'key': expected_key,
        'url': f's3://content-factory/{expected_key}',
        'content_type': 'text/plain',
        'size_bytes': 58,
        'etag': 'etag-packet38',
    }


def test_execution_trace_failed_event_includes_lifecycle_metrics_and_rejection_marker(client):
    owner, job_id, _, _ = seed_job_fixture('Packet 38 failed details')

    claim = client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers())
    assert claim.status_code == 200
    heartbeat = client.post(f'/api/v1/jobs/{job_id}/heartbeat', json={'stage_name': 'persist-artifact'}, headers=worker_headers())
    assert heartbeat.status_code == 200
    fail = client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'processing error: artifact key escaped job scope'},
        headers=worker_headers(),
    )
    assert fail.status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    failed_event = trace['events'][2]
    assert failed_event['event'] == 'failed'
    assert failed_event['worker_id'] == 'packet38-worker'
    assert failed_event['failure_reason'] == 'processing error: artifact key escaped job scope'
    assert failed_event['artifact_scope_status'] == 'rejected'
    assert failed_event['lifecycle_seconds'] >= 0
    assert failed_event['stage_count'] == 3
