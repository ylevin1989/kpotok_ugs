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



def seed_org_with_two_owners():
    owner1 = seed_user('owner1-p12@example.com')
    owner2 = seed_user('owner2-p12@example.com')
    reviewer = seed_user('reviewer-p12@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet12', slug='uno-packet12', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner1.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner2.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner1, owner2, reviewer, org



def seed_org_with_single_owner():
    owner = seed_user('owner-single-p12@example.com')
    reviewer = seed_user('reviewer-single-p12@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet12 Single', slug='uno-packet12-single', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, reviewer, org



def get_membership_id(org_id, user_id):
    db = SessionLocal()
    membership = db.query(OrganizationMembership).filter_by(organization_id=org_id, user_id=user_id).one()
    membership_id = membership.id
    db.close()
    return membership_id



def test_owner_can_downgrade_other_owner_when_another_owner_remains(client):
    owner1, owner2, _, org = seed_org_with_two_owners()
    owner2_membership_id = get_membership_id(org.id, owner2.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{owner2_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner1.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_manager'



def test_owner_cannot_downgrade_last_remaining_owner(client):
    owner, _, org = seed_org_with_single_owner()
    owner_membership_id = get_membership_id(org.id, owner.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{owner_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Cannot change the last owner role'



def test_owner_can_self_downgrade_when_another_owner_remains(client):
    owner1, owner2, _, org = seed_org_with_two_owners()
    owner1_membership_id = get_membership_id(org.id, owner1.id)

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{owner1_membership_id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner1.email),
    )

    assert response.status_code == 200
    assert response.json()['role'] == 'client_manager'
