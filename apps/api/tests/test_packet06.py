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


def seed_org_with_members():
    owner = seed_user('owner-p6@example.com')
    manager = seed_user('manager-p6@example.com')
    reviewer = seed_user('reviewer-p6@example.com')
    invitee = seed_user('invitee-p6@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet06', slug='uno-packet06', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, manager, reviewer, invitee, org


def test_manager_can_list_organization_members(client):
    _, manager, _, _, org = seed_org_with_members()

    response = client.get(f'/api/v1/organizations/{org.id}/members', headers=auth_headers(client, manager.email))

    assert response.status_code == 200
    items = response.json()['items']
    assert len(items) == 3
    assert {item['role'] for item in items} == {'client_owner', 'client_manager', 'client_reviewer'}



def test_reviewer_cannot_list_organization_members(client):
    _, _, reviewer, _, org = seed_org_with_members()

    response = client.get(f'/api/v1/organizations/{org.id}/members', headers=auth_headers(client, reviewer.email))

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_manager_can_add_existing_user_to_organization(client):
    _, manager, _, invitee, org = seed_org_with_members()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': invitee.email, 'role': 'client_reviewer'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 201
    data = response.json()
    assert data['email'] == invitee.email
    assert data['role'] == 'client_reviewer'



def test_reviewer_cannot_add_member(client):
    _, _, reviewer, invitee, org = seed_org_with_members()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': invitee.email, 'role': 'client_reviewer'},
        headers=auth_headers(client, reviewer.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_owner_can_update_member_role(client):
    owner, _, reviewer, _, org = seed_org_with_members()
    db = SessionLocal()
    membership = db.query(OrganizationMembership).filter_by(organization_id=org.id, user_id=reviewer.id).one()
    membership_id = membership.id
    db.close()

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['email'] == reviewer.email
    assert data['role'] == 'client_manager'
