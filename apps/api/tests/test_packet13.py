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



def seed_org_with_roles():
    owner1 = seed_user('owner1-p13@example.com')
    owner2 = seed_user('owner2-p13@example.com')
    manager = seed_user('manager-p13@example.com')
    reviewer = seed_user('reviewer-p13@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet13', slug='uno-packet13', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner1.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner2.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner1, owner2, manager, reviewer, org



def get_membership_id(org_id, user_id):
    db = SessionLocal()
    membership = db.query(OrganizationMembership).filter_by(organization_id=org_id, user_id=user_id).one()
    membership_id = membership.id
    db.close()
    return membership_id



def test_manager_can_promote_reviewer_to_manager(client):
    _, _, manager, reviewer, org = seed_org_with_roles()
    reviewer_membership_id = get_membership_id(org.id, reviewer.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_manager'



def test_manager_can_demote_manager_to_reviewer(client):
    owner1, _, manager, _, org = seed_org_with_roles()
    manager_membership_id = get_membership_id(org.id, manager.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{manager_membership_id}',
        json={'role': 'client_reviewer'},
        headers=auth_headers(client, owner1.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_reviewer'



def test_owner_can_downgrade_other_owner_to_reviewer_when_another_owner_remains(client):
    owner1, owner2, _, _, org = seed_org_with_roles()
    owner2_membership_id = get_membership_id(org.id, owner2.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{owner2_membership_id}',
        json={'role': 'client_reviewer'},
        headers=auth_headers(client, owner1.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_reviewer'



def test_owner_can_noop_update_reviewer_role(client):
    owner1, _, _, reviewer, org = seed_org_with_roles()
    reviewer_membership_id = get_membership_id(org.id, reviewer.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership_id}',
        json={'role': 'client_reviewer'},
        headers=auth_headers(client, owner1.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_reviewer'
