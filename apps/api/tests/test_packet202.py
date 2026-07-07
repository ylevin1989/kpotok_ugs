from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.user import User
from app.db.session import SessionLocal


def seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def seed_brand_fixture():
    owner = seed_user('owner-p202@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet202', slug='uno-packet202', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Paused metadata brand', slug='paused-metadata-brand')
    db.add(brand)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.close()
    return owner, str(org.id), str(brand.id)


def test_paused_brand_allows_metadata_updates_but_blocks_content_writes(client):
    owner, org_id, brand_id = seed_brand_fixture()

    paused = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    rename = client.patch(
        f'/api/v1/brands/{brand_id}',
        json={'name': 'Paused metadata brand v2'},
        headers=auth_headers(client, owner.email),
    )
    assert rename.status_code == 200
    assert rename.json()['name'] == 'Paused metadata brand v2'
    assert rename.json()['status'] == 'paused'

    product = client.post(
        '/api/v1/products',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'sku': 'paused-brand-product-p202',
            'name': 'Paused Brand Product P202',
            'category': 'lifecycle',
            'description': 'Paused brands should still be metadata-writable but block content creation.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert product.status_code == 409
    assert product.json()['detail'] == 'Paused brand is read-only for content writes'
