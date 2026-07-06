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


def seed_org_for_delete_policy():
    owner = seed_user('owner-p15@example.com')
    owner2 = seed_user('owner2-p15@example.com')
    owner3 = seed_user('owner3-p15@example.com')
    manager = seed_user('manager-p15@example.com')
    reviewer = seed_user('reviewer-p15@example.com')
    manager2 = seed_user('manager2-p15@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet15', slug='uno-packet15', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner2.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner3.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager2.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, owner2, owner3, manager, reviewer, manager2, org


def get_membership_id(org_id, user_id):
    db = SessionLocal()
    membership = db.query(OrganizationMembership).filter_by(organization_id=org_id, user_id=user_id).one()
    membership_id = membership.id
    db.close()
    return membership_id


def test_manager_can_delete_reviewer_membership(client):
    _, _, _, manager, reviewer, _, org = seed_org_for_delete_policy()
    reviewer_membership_id = get_membership_id(org.id, reviewer.id)

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership_id}',
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 204


def test_manager_can_delete_manager_membership(client):
    _, _, _, manager, _, manager2, org = seed_org_for_delete_policy()
    manager2_membership_id = get_membership_id(org.id, manager2.id)

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{manager2_membership_id}',
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 204


def test_manager_cannot_delete_owner_membership(client):
    _, owner2, _, manager, _, _, org = seed_org_for_delete_policy()
    owner2_membership_id = get_membership_id(org.id, owner2.id)

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{owner2_membership_id}',
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Only owners can modify owner memberships'


def test_owner_can_delete_other_owner_while_one_owner_remains(client):
    owner, owner2, _, _, _, _, org = seed_org_for_delete_policy()
    owner2_membership_id = get_membership_id(org.id, owner2.id)

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{owner2_membership_id}',
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 204


def test_owner_cannot_delete_own_membership(client):
    owner, _, _, _, _, _, org = seed_org_for_delete_policy()
    owner_membership_id = get_membership_id(org.id, owner.id)

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{owner_membership_id}',
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Cannot remove your own membership'
