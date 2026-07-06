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


def seed_org_with_brand(owner_role: MembershipRole = MembershipRole.CLIENT_OWNER):
    owner = seed_user('owner-p5@example.com')
    reviewer = seed_user('reviewer-p5@example.com')
    outsider = seed_user('outsider-p5@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet05', slug='uno-packet05', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Packet05 Brand', slug='packet05-brand')
    db.add(brand)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=owner_role))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.close()
    return owner, reviewer, outsider, org, brand


def test_reviewer_can_list_brands_for_accessible_org(client):
    _, reviewer, _, org, brand = seed_org_with_brand()

    response = client.get(f'/api/v1/brands?organization_id={org.id}', headers=auth_headers(client, reviewer.email))

    assert response.status_code == 200
    items = response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == str(brand.id)



def test_reviewer_cannot_create_brand(client):
    _, reviewer, _, org, _ = seed_org_with_brand()

    response = client.post(
        '/api/v1/brands',
        json={'organization_id': str(org.id), 'name': 'Forbidden Brand', 'slug': 'forbidden-brand'},
        headers=auth_headers(client, reviewer.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_manager_can_delete_brand(client):
    owner, _, _, _, brand = seed_org_with_brand(MembershipRole.CLIENT_MANAGER)

    response = client.delete(f'/api/v1/brands/{brand.id}', headers=auth_headers(client, owner.email))

    assert response.status_code == 204

    db = SessionLocal()
    deleted = db.get(Brand, brand.id)
    db.close()
    assert deleted is None



def test_reviewer_cannot_delete_brand(client):
    _, reviewer, _, _, brand = seed_org_with_brand()

    response = client.delete(f'/api/v1/brands/{brand.id}', headers=auth_headers(client, reviewer.email))

    assert response.status_code == 403
    assert response.json()['detail'] == 'Manager access required'



def test_outsider_cannot_read_brand_detail(client):
    _, _, outsider, _, brand = seed_org_with_brand()

    response = client.get(f'/api/v1/brands/{brand.id}', headers=auth_headers(client, outsider.email))

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
