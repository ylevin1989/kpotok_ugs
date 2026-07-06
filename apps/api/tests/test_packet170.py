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
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': 'packet170-worker'}


def seed_job_fixture(title: str):
    owner = seed_user(f"{title.replace(' ', '-').lower()}@example.com")
    db = SessionLocal()
    org = Organization(name='Uno Packet170', slug=f"uno-packet170-{title.replace(' ', '-').lower()}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 170', slug=f"rocket-tea-p170-{title.replace(' ', '-').lower()}")
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 170', content='Need a campaign launch plan 170.')
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


def test_execution_trace_completed_validation_result_is_structured(client):
    owner, job_id, org_id, brand_id = seed_job_fixture('Packet 170 completed validation result')
    expected_key = f'organizations/{org_id}/brands/{brand_id}/jobs/{job_id}/artifacts/result.txt'

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers()).status_code == 200
    assert client.post(f'/api/v1/jobs/{job_id}/heartbeat', json={'stage_name': 'render-output'}, headers=worker_headers()).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/complete',
        json={
            'output_text': 'packet170-result',
            'output_artifact_key': expected_key,
            'output_artifact_url': f's3://content-factory/{expected_key}',
            'output_artifact_content_type': 'text/plain',
            'output_artifact_size_bytes': 58,
            'output_artifact_etag': 'etag-packet170',
        },
        headers=worker_headers(),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    expected_validation_result = {
        'status': 'validated',
        'artifact_scope_status': 'validated',
        'artifact_key': expected_key,
    }
    assert trace['validation_result'] == expected_validation_result
    assert trace['events'][2]['validation_result'] == expected_validation_result


def test_execution_trace_failed_validation_result_is_structured(client):
    owner, job_id, _, _ = seed_job_fixture('Packet 170 failed validation result')

    assert client.post(f'/api/v1/jobs/{job_id}/claim', headers=worker_headers()).status_code == 200
    assert client.post(f'/api/v1/jobs/{job_id}/heartbeat', json={'stage_name': 'persist-artifact'}, headers=worker_headers()).status_code == 200
    assert client.post(
        f'/api/v1/jobs/{job_id}/fail',
        json={'error_message': 'processing error: artifact key escaped job scope'},
        headers=worker_headers(),
    ).status_code == 200

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))
    assert response.status_code == 200
    trace = response.json()['execution_trace']

    expected_validation_result = {
        'status': 'rejected',
        'artifact_scope_status': 'rejected',
        'reason': 'processing error: artifact key escaped job scope',
        'failure_code': 'artifact_scope_rejection',
    }
    assert trace['validation_result'] == expected_validation_result
    assert trace['events'][2]['validation_result'] == expected_validation_result
