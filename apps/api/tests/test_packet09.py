from app.core.security import hash_password
from app.db.models.brand import Brand
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


def seed_archived_org_with_brand_and_member():
    owner = seed_user('owner-p9@example.com')
    reviewer = seed_user('reviewer-p9@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet09', slug='uno-packet09', status=OrganizationStatus.ARCHIVED)
    db.add(org)
    db.flush()
    owner_membership = OrganizationMembership(
        organization_id=org.id,
        user_id=owner.id,
        role=MembershipRole.CLIENT_OWNER,
    )
    reviewer_membership = OrganizationMembership(
        organization_id=org.id,
        user_id=reviewer.id,
        role=MembershipRole.CLIENT_REVIEWER,
    )
    brand = Brand(organization_id=org.id, name='Packet09 Brand', slug='packet09-brand')
    db.add_all([owner_membership, reviewer_membership, brand])
    db.commit()
    db.refresh(org)
    db.refresh(reviewer_membership)
    db.refresh(brand)
    db.close()
    return owner, reviewer_membership, brand, org


def test_cannot_update_member_in_archived_organization(client):
    owner, reviewer_membership, _, org = seed_archived_org_with_brand_and_member()

    response = client.patch(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership.id}',
        json={'role': 'client_manager'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_cannot_delete_member_in_archived_organization(client):
    owner, reviewer_membership, _, org = seed_archived_org_with_brand_and_member()

    response = client.delete(
        f'/api/v1/organizations/{org.id}/members/{reviewer_membership.id}',
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_cannot_update_brand_in_archived_organization(client):
    owner, _, brand, _ = seed_archived_org_with_brand_and_member()

    response = client.patch(
        f'/api/v1/brands/{brand.id}',
        json={'name': 'Renamed Archived Brand'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_cannot_delete_brand_in_archived_organization(client):
    owner, _, brand, _ = seed_archived_org_with_brand_and_member()

    response = client.delete(
        f'/api/v1/brands/{brand.id}',
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'
