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


def seed_org_with_members_and_candidates():
    owner = seed_user('owner-p14@example.com')
    manager = seed_user('manager-p14@example.com')
    reviewer = seed_user('reviewer-p14@example.com')
    candidate_manager = seed_user('candidate-manager-p14@example.com')
    candidate_reviewer = seed_user('candidate-reviewer-p14@example.com')
    candidate_owner = seed_user('candidate-owner-p14@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet14', slug='uno-packet14', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, manager, reviewer, candidate_manager, candidate_reviewer, candidate_owner, org


def get_membership_id(org_id, user_id):
    db = SessionLocal()
    membership = db.query(OrganizationMembership).filter_by(organization_id=org_id, user_id=user_id).one()
    membership_id = membership.id
    db.close()
    return membership_id


def test_manager_can_add_new_manager(client):
    _, manager, _, candidate_manager, _, _, org = seed_org_with_members_and_candidates()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': candidate_manager.email, 'role': 'client_manager'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 201
    assert response.json()['role'] == 'client_manager'


def test_manager_can_add_new_reviewer(client):
    _, manager, _, _, candidate_reviewer, _, org = seed_org_with_members_and_candidates()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': candidate_reviewer.email, 'role': 'client_reviewer'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 201
    assert response.json()['role'] == 'client_reviewer'


def test_owner_can_add_new_owner(client):
    owner, _, _, _, _, candidate_owner, org = seed_org_with_members_and_candidates()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': candidate_owner.email, 'role': 'client_owner'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    assert response.json()['role'] == 'client_owner'


def test_manager_cannot_add_new_owner(client):
    _, manager, _, _, _, candidate_owner, org = seed_org_with_members_and_candidates()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': candidate_owner.email, 'role': 'client_owner'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Only owners can assign owner role'


def test_manager_can_promote_reviewer_to_manager(client):
    _, manager, reviewer, _, _, _, org = seed_org_with_members_and_candidates()
    reviewer_membership_id = get_membership_id(org.id, reviewer.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_manager'


def test_manager_cannot_promote_reviewer_to_owner(client):
    _, manager, reviewer, _, _, _, org = seed_org_with_members_and_candidates()
    reviewer_membership_id = get_membership_id(org.id, reviewer.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership_id}',
        json={'role': 'client_owner'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Only owners can assign owner role'
