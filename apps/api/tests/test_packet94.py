from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


EXPECTED_SEO_ROLE_IDS = ['mike', 'emma', 'iris', 'sarah', 'alex', 'david']
EXPECTED_DEFAULT_ROLE_IDS = ['mike', 'emma', 'iris', 'alex', 'david']


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


def seed_job_scope(seed_slug: str):
    owner = seed_user(f'{seed_slug}-owner@example.com')
    db = SessionLocal()
    org = Organization(name=f'{seed_slug} Org', slug=f'{seed_slug}-org', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name=f'{seed_slug} Brand', slug=f'{seed_slug}-brand')
    db.add(brand)
    db.flush()
    brief = Brief(organization_id=org.id, brand_id=brand.id, title=f'{seed_slug} Brief', content='Need internal role plan coverage.')
    db.add(brief)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    payload = {
        'owner_email': owner.email,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'brief_id': str(brief.id),
    }
    db.close()
    return payload


def test_create_job_persists_selected_execution_profile_and_internal_role_plan(client):
    fixture = seed_job_scope('packet94-selected')

    create_response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'brief_id': fixture['brief_id'],
            'title': 'Packet94 SEO content job',
            'execution_profile': 'seo_content',
        },
        headers=auth_headers(client, fixture['owner_email']),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['execution_profile'] == 'seo_content'
    assert [item['role_id'] for item in created['internal_role_plan']] == EXPECTED_SEO_ROLE_IDS
    assert created['internal_role_plan'][0]['label'] == 'Mike'
    assert created['internal_role_plan'][3]['role_id'] == 'sarah'

    get_response = client.get(f"/api/v1/jobs/{created['id']}", headers=auth_headers(client, fixture['owner_email']))
    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['execution_profile'] == 'seo_content'
    assert [item['role_id'] for item in fetched['internal_role_plan']] == EXPECTED_SEO_ROLE_IDS


def test_create_job_defaults_execution_profile_and_exposes_internal_role_plan_in_list(client):
    fixture = seed_job_scope('packet94-default')

    create_response = client.post(
        '/api/v1/jobs',
        json={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'brief_id': fixture['brief_id'],
            'title': 'Packet94 default content job',
        },
        headers=auth_headers(client, fixture['owner_email']),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['execution_profile'] == 'general_content'
    assert [item['role_id'] for item in created['internal_role_plan']] == EXPECTED_DEFAULT_ROLE_IDS

    list_response = client.get(
        '/api/v1/jobs',
        params={
            'organization_id': fixture['organization_id'],
            'brand_id': fixture['brand_id'],
            'brief_id': fixture['brief_id'],
        },
        headers=auth_headers(client, fixture['owner_email']),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']
    assert items[0]['execution_profile'] == 'general_content'
    assert [item['role_id'] for item in items[0]['internal_role_plan']] == EXPECTED_DEFAULT_ROLE_IDS
