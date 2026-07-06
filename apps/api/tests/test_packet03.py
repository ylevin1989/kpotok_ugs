from app.core.security import hash_password
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str = 'yakov@example.com', password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, full_name='Yakov', password_hash=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email='yakov@example.com', password='test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    token = response.json()['access_token']
    return {'Authorization': f'Bearer {token}'}


def test_create_and_list_organizations_for_current_user(client):
    seed_user()

    headers = auth_headers(client)
    create_response = client.post('/api/v1/organizations', json={'name': 'Uno AI', 'slug': 'uno-ai'}, headers=headers)

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['name'] == 'Uno AI'
    assert created['slug'] == 'uno-ai'
    assert created['status'] == 'active'
    assert created['membership_role'] == 'client_owner'

    list_response = client.get('/api/v1/organizations', headers=headers)

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['slug'] == 'uno-ai'


def test_create_and_list_brands_only_inside_accessible_organization(client):
    user = seed_user()
    db = SessionLocal()
    org = Organization(name='Uno AI', slug='uno-ai', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=user.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.close()

    headers = auth_headers(client)
    create_response = client.post(
        '/api/v1/brands',
        json={
            'organization_id': str(org.id),
            'name': 'Rocket Tea',
            'slug': 'rocket-tea',
        },
        headers=headers,
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['name'] == 'Rocket Tea'
    assert created['slug'] == 'rocket-tea'
    assert created['organization_id'] == str(org.id)

    list_response = client.get(f'/api/v1/brands?organization_id={org.id}', headers=headers)

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['slug'] == 'rocket-tea'
