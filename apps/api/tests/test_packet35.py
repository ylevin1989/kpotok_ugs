from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str) -> User:
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password('test12345'))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str) -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': 'test12345'})
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_get_job_exposes_explicit_scope_block(client):
    owner = seed_user('owner-p35-scope@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet35', slug='uno-packet35', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 35', slug='rocket-tea-p35')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title='Launch brief 35', content='Need a campaign launch plan 35.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    from app.db.models.job import Job
    job = Job(
        organization_id=org.id,
        brand_id=brand.id,
        brief_id=brief.id,
        title='Read job scope contract',
        status='queued',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    org_id = org.id
    brand_id = brand.id
    brief_id = brief.id
    db.close()

    response = client.get(f'/api/v1/jobs/{job_id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 200
    body = response.json()
    assert body['scope'] == {
        'organization_id': str(org_id),
        'brand_id': str(brand_id),
        'brief_id': str(brief_id),
    }
