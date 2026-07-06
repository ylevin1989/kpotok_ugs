from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
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


def seed_paused_audience_segment_fixture():
    owner = seed_user('owner-p186@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet186', slug='uno-packet186', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 186', slug='rocket-tea-p186')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-186-001',
        name='Rocket Tea Starter Kit 186',
        category='starter-kit',
        description='Starter kit for paused audience-segment regression.',
    )
    db.add(product)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    org_id = str(org.id)
    brand_id = str(brand.id)
    product_id = str(product.id)
    db.close()
    return owner, org_id, brand_id, product_id


def test_paused_organization_blocks_audience_segment_creation(client):
    owner, org_id, brand_id, product_id = seed_paused_audience_segment_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/audience-segments',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'product_id': product_id,
            'scope': 'product',
            'name': 'Paused segment',
            'description': 'Paused orgs should not accept new audience segments.',
            'pain_points': ['Too much friction'],
            'goals': ['Buy faster'],
            'objections': ['Too expensive'],
            'keywords': ['starter kit', 'quick setup'],
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
