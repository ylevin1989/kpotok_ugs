import json

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_legacy_trace_job(title: str = 'Packet 90 legacy execution trace list jobs'):
    db = SessionLocal()
    owner = User(email='packet90-owner@example.com', password_hash=hash_password('test12345'), is_active=True)
    db.add(owner)
    db.flush()

    org = Organization(name='Packet90 Org', slug='packet90-org', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()

    brand = Brand(organization_id=org.id, name='Packet90 Brand', slug='packet90-brand')
    db.add(brand)
    db.flush()

    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Packet90 Brief', content='Legacy execution trace fixture')
    db.add(brief)
    db.flush()

    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))

    legacy_trace = {
        'scope': {
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'brief_id': str(brief.id),
        },
        'stage_history': ['claimed', 'completed'],
        'events': [
            {'event': 'claimed', 'at': '2026-07-04T00:00:00Z'},
            {'event': 'completed', 'at': '2026-07-04T00:00:03Z'},
        ],
        'final_status': 'completed',
        'last_progress': {'progress_percent': 100, 'progress_message': 'Done'},
    }

    job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title=title,
        status='completed',
        output_text='legacy-output',
        execution_trace_json=json.dumps(legacy_trace),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    payload = {
        'owner_email': owner.email,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'brief_id': str(brief.id),
        'job_id': str(job.id),
    }
    db.close()
    return payload


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def test_list_jobs_normalizes_legacy_execution_trace_shape(client):
    fixture = seed_legacy_trace_job()

    response = client.get(
        '/api/v1/jobs',
        params={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'brief_id': fixture['brief_id'],
        },
        headers=auth_headers(client, fixture['owner_email']),
    )

    assert response.status_code == 200
    payload = response.json()
    assert len(payload['items']) == 1
    item = payload['items'][0]
    assert item['id'] == fixture['job_id']
    assert item['execution_trace']['stage_timings'] == []
    assert item['execution_trace']['progress_history'] == []
    assert item['execution_trace']['stage_transition_counts'] == {}
    assert item['execution_trace']['final_status'] == 'completed'
    assert item['output_text'] == 'legacy-output'
