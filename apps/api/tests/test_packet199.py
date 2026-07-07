from app.core.security import hash_password
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345', full_name: str | None = None) -> User:
    db = SessionLocal()
    user = User(
        email=email,
        full_name=full_name or email.split('@')[0].title(),
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


def seed_org_with_owner():
    owner = seed_user('owner-p199@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet199', slug='uno-packet199', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, org


def test_register_creates_active_user_and_login_works(client):
    response = client.post(
        '/api/v1/auth/register',
        json={
            'email': 'register-p199@example.com',
            'full_name': 'Register Packet',
            'password': 'test12345',
        },
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload['user']['email'] == 'register-p199@example.com'
    assert payload['user']['full_name'] == 'Register Packet'
    assert payload['user']['is_active'] is True
    assert payload['access_token']

    login = client.post('/api/v1/auth/login', json={'email': 'register-p199@example.com', 'password': 'test12345'})
    assert login.status_code == 200

    me = client.get('/api/v1/auth/me', headers={'Authorization': f"Bearer {payload['access_token']}"})
    assert me.status_code == 200
    assert me.json()['user']['email'] == 'register-p199@example.com'


def test_owner_can_add_registered_user_to_organization(client):
    owner, org = seed_org_with_owner()
    teammate = seed_user('teammate-p199@example.com')

    add_response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        headers=auth_headers(client, owner.email),
        json={'email': teammate.email, 'role': 'client_manager'},
    )

    assert add_response.status_code == 201
    assert add_response.json()['email'] == teammate.email
    assert add_response.json()['role'] == 'client_manager'

    list_response = client.get(
        f'/api/v1/organizations/{org.id}/members',
        headers=auth_headers(client, owner.email),
    )
    assert list_response.status_code == 200
    emails = {item['email'] for item in list_response.json()['items']}
    assert teammate.email in emails
