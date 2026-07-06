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


def seed_archived_org():
    owner = seed_user('owner-p8@example.com')
    invitee = seed_user('invitee-p8@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet08', slug='uno-packet08', status=OrganizationStatus.ARCHIVED)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, invitee, org


def test_archived_organization_detail_is_readable(client):
    owner, _, org = seed_archived_org()

    response = client.get(f'/api/v1/organizations/{org.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 200
    assert response.json()['status'] == 'archived'


def test_archived_organization_cannot_be_updated(client):
    owner, _, org = seed_archived_org()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Renamed Archived Org'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_cannot_add_member_to_archived_organization(client):
    owner, invitee, org = seed_archived_org()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': invitee.email, 'role': 'client_reviewer'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_cannot_create_brand_in_archived_organization(client):
    owner, _, org = seed_archived_org()

    response = client.post(
        '/api/v1/brands',
        json={'organization_id': str(org.id), 'name': 'Archived Brand', 'slug': 'archived-brand'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'
