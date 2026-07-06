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


def seed_org_for_status_policy():
    owner = seed_user('owner-p17@example.com')
    manager = seed_user('manager-p17@example.com')
    reviewer = seed_user('reviewer-p17@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet17', slug='uno-packet17', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, manager, reviewer, org


def test_manager_can_still_update_organization_name_without_status_change(client):
    _, manager, _, org = seed_org_for_status_policy()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Uno Packet17 Renamed', 'slug': 'uno-packet17-renamed'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'Uno Packet17 Renamed'
    assert data['slug'] == 'uno-packet17-renamed'
    assert data['status'] == 'active'
    assert data['membership_role'] == 'client_manager'


def test_manager_cannot_change_organization_status(client):
    _, manager, _, org = seed_org_for_status_policy()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'status': 'paused'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Only owners can change organization status'


def test_owner_can_change_organization_status(client):
    owner, _, _, org = seed_org_for_status_policy()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['status'] == 'paused'
    assert data['membership_role'] == 'client_owner'


def test_reviewer_still_cannot_update_organization(client):
    _, _, reviewer, org = seed_org_for_status_policy()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Should Fail', 'status': 'paused'},
        headers=auth_headers(client, reviewer.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'
