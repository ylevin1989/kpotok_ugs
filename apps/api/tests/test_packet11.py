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
    owner = seed_user('owner-p11@example.com')
    manager = seed_user('manager-p11@example.com')
    invitee = seed_user('invitee-p11@example.com')
    invitee2 = seed_user('invitee2-p11@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet11', slug='uno-packet11', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(org)
    db.close()
    return owner, manager, invitee, invitee2, org



def test_manager_cannot_add_member_as_owner(client):
    _, manager, invitee, _, org = seed_org_with_members()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': invitee.email, 'role': 'client_owner'},
        headers=auth_headers(client, manager.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Only owners can assign owner role'



def test_owner_can_add_member_as_owner(client):
    owner, _, _, invitee2, org = seed_org_with_members()

    response = client.post(
        f'/api/v1/organizations/{org.id}/members',
        json={'email': invitee2.email, 'role': 'client_owner'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    assert response.json()['email'] == invitee2.email
    assert response.json()['role'] == 'client_owner'
