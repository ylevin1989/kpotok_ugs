from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, full_name=email.split('@')[0].title(), password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_org_with_member(member_role: MembershipRole = MembershipRole.CLIENT_OWNER):
    owner = seed_user('owner@example.com')
    viewer = seed_user('viewer@example.com')
    db = SessionLocal()
    org = Organization(name='Uno AI', slug='uno-ai', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea')
    db.add(brand)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=member_role))
    db.add(OrganizationMembership(organization_id=org.id, user_id=viewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.close()
    return owner, viewer, org, brand


def test_get_organization_detail_for_member(client):
    owner, _, org, _ = seed_org_with_member()

    response = client.get(f'/api/v1/organizations/{org.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == str(org.id)
    assert data['slug'] == 'uno-ai'
    assert data['membership_role'] == 'client_owner'



def test_update_organization_requires_manager_role(client):
    _, viewer, org, _ = seed_org_with_member()

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Uno AI Updated', 'status': 'paused'},
        headers=auth_headers(client, viewer.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_manager_can_update_organization(client):
    owner, _, org, _ = seed_org_with_member(MembershipRole.CLIENT_MANAGER)

    response = client.patch(
        f'/api/v1/organizations/{org.id}',
        json={'name': 'Uno AI Updated', 'slug': 'uno-ai-updated'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'Uno AI Updated'
    assert data['slug'] == 'uno-ai-updated'
    assert data['status'] == 'active'
    assert data['membership_role'] == 'client_manager'



def test_get_brand_detail_for_member(client):
    owner, _, _, brand = seed_org_with_member()

    response = client.get(f'/api/v1/brands/{brand.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 200
    data = response.json()
    assert data['id'] == str(brand.id)
    assert data['slug'] == 'rocket-tea'



def test_update_brand_requires_manager_role(client):
    _, viewer, _, brand = seed_org_with_member()

    response = client.patch(
        f'/api/v1/brands/{brand.id}',
        json={'name': 'Rocket Tea 2', 'slug': 'rocket-tea-2'},
        headers=auth_headers(client, viewer.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_manager_can_update_brand(client):
    owner, _, _, brand = seed_org_with_member(MembershipRole.CLIENT_MANAGER)

    response = client.patch(
        f'/api/v1/brands/{brand.id}',
        json={'name': 'Rocket Tea 2', 'slug': 'rocket-tea-2'},
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == 'Rocket Tea 2'
    assert data['slug'] == 'rocket-tea-2'
