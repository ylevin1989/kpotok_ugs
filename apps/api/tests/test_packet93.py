from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(
        email=email,
        full_name=email.split('@')[0].title(),
        password_hash=hash_password(password),
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_brand_delete_fixture():
    owner = seed_user('owner-p93@example.com')
    db = SessionLocal()
    organization = Organization(name='Uno Packet93', slug='uno-packet93', status=OrganizationStatus.ACTIVE)
    db.add(organization)
    db.flush()
    db.add(
        OrganizationMembership(
            organization_id=organization.id,
            user_id=owner.id,
            role=MembershipRole.CLIENT_OWNER,
        )
    )

    empty_brand = Brand(organization_id=organization.id, name='Empty Brand', slug='empty-brand')
    populated_brand = Brand(organization_id=organization.id, name='Populated Brand', slug='populated-brand')
    db.add_all([empty_brand, populated_brand])
    db.flush()

    brief = Brief(
        organization_id=organization.id,
        brand_id=populated_brand.id,
        title='Packet93 Brief',
        content='Delete-policy fixture',
    )
    db.add(brief)
    db.flush()

    job = Job(
        organization_id=organization.id,
        brand_id=populated_brand.id,
        brief_id=brief.id,
        title='Packet93 Job',
        status='completed',
    )
    db.add(job)
    db.commit()
    db.refresh(empty_brand)
    db.refresh(populated_brand)
    db.close()
    return owner, empty_brand, populated_brand


def test_empty_brand_can_be_hard_deleted(client):
    owner, empty_brand, _ = seed_brand_delete_fixture()

    response = client.delete(f'/api/v1/brands/{empty_brand.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 204

    get_response = client.get(f'/api/v1/brands/{empty_brand.id}', headers=auth_headers(client, owner.email))
    assert get_response.status_code == 404


def test_brand_with_briefs_and_jobs_cannot_be_hard_deleted(client):
    owner, _, populated_brand = seed_brand_delete_fixture()

    response = client.delete(f'/api/v1/brands/{populated_brand.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 409
    assert response.json()['detail'] == 'Brand with briefs or jobs cannot be hard-deleted'

    get_response = client.get(f'/api/v1/brands/{populated_brand.id}', headers=auth_headers(client, owner.email))
    assert get_response.status_code == 200
