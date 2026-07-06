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


def seed_archived_org_policy_fixture():
    owner = seed_user('owner-p18@example.com')
    manager = seed_user('manager-p18@example.com')
    reviewer = seed_user('reviewer-p18@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet18', slug='uno-packet18', status=OrganizationStatus.ARCHIVED)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, manager, reviewer, org


def test_owner_can_unarchive_archived_organization_via_status_patch(client):
    owner, _, _, org = seed_archived_org_policy_fixture()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'status': 'active'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'active'
    assert data['membership_role'] == 'client_owner'


def test_manager_cannot_unarchive_archived_organization(client):
    _, manager, _, org = seed_archived_org_policy_fixture()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'status': 'active'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_archived_org_still_blocks_regular_metadata_edits(client):
    owner, _, _, org = seed_archived_org_policy_fixture()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Should Stay Frozen'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_archived_org_rejects_unarchive_plus_metadata_edit_in_same_request(client):
    owner, _, _, org = seed_archived_org_policy_fixture()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'status': 'active', 'name': 'Sneaky Rename'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'
