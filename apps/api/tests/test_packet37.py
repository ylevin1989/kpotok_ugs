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
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': 'packet37-worker'}


def seed_job_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet37', slug=f"uno-packet37-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 37', slug=f"rocket-tea-p37-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 37', content='Need a campaign launch plan 37.')
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
    brief_id = str(brief.id)
    db.close()
    return owner, job_id, org_id, brand_id, brief_id


def test_execution_trace_exposes_structured_completed_events(client):
    owner, job_id, org_id, brand_id, brief_id = seed_job_fixture('Packet 37 completed events')
    expected_key = f'organizations/{org_id}/brands/{brand_id}/jobs/{job_id}/artifacts/result.txt'

    claim = client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers())
    assert claim.status_code == 200
    heartbeat = client.post(f'/api/v1/jobs/{job_id}/heartbeat', json={'stage_name': 'render-output'}, headers=worker_headers())
    assert heartbeat.status_code == 200
    complete = client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={
            'output_text': 'packet37-result',
            'output_artifact_key': expected_key,
            'output_artifact_url': f's3://content-factory/{expected_key}',
            'output_artifact_content_type': 'text/plain',
        },
        headers=worker_headers(),
    )
    assert complete.status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['scope'] == {
        'organization_id': org_id,
        'brand_id': brand_id,
        'brief_id': brief_id,
    }
    assert trace['stage_history'] == ['claimed', 'render-output', 'completed']
    assert trace['artifact_scope_status'] == 'validated'
    assert trace['final_status'] == 'completed'
    assert trace['failure_reason'] is None

    assert [event['event'] for event in trace['events']] == ['claimed', 'heartbeat', 'completed']
    assert trace['events'][0]['worker_id'] == 'packet37-worker'
    assert trace['events'][1]['stage_name'] == 'render-output'
    assert trace['events'][1]['worker_id'] == 'packet37-worker'
    assert trace['events'][2]['artifact_scope_status'] == 'validated'
    assert trace['events'][2]['worker_id'] == 'packet37-worker'
    for event in trace['events']:
        assert event['at']


def test_execution_trace_exposes_structured_failed_events(client):
    owner, job_id, org_id, brand_id, brief_id = seed_job_fixture('Packet 37 failed events')

    claim = client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers())
    assert claim.status_code == 200
    fail = client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'processing error: render exploded'},
        headers=worker_headers(),
    )
    assert fail.status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    assert trace['scope'] == {
        'organization_id': org_id,
        'brand_id': brand_id,
        'brief_id': brief_id,
    }
    assert trace['stage_history'] == ['claimed', 'failed']
    assert trace['final_status'] == 'failed'
    assert trace['failure_reason'] == 'processing error: render exploded'
    assert [event['event'] for event in trace['events']] == ['claimed', 'failed']
    assert trace['events'][0]['worker_id'] == 'packet37-worker'
    assert trace['events'][1]['worker_id'] == 'packet37-worker'
    assert trace['events'][1]['failure_reason'] == 'processing error: render exploded'
    for event in trace['events']:
        assert event['at']
