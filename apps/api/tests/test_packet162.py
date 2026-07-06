import pytest

from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.media_asset import MediaAsset
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
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


def seed_media_asset_fixture(archived: bool = False):
    owner = seed_user('owner-p162@example.com')
    reviewer = seed_user('reviewer-p162@example.com')
    outsider = seed_user('outsider-p162@example.com')
    other_owner = seed_user('other-owner-p162@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet162',
        slug='uno-packet162',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    other_org = Organization(name='Other Packet162', slug='other-packet162', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.add(other_org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea', slug='rocket-tea-p162')
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p162')
    db.add(brand)
    db.add(other_brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-162-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for product-scoped media.',
    )
    other_product = Product(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        sku='SKU-OTHER-162',
        name='Other Starter Kit',
        category='starter-kit',
        description='Belongs to another organization.',
    )
    db.add(product)
    db.add(other_product)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.add(OrganizationMembership(organization_id=other_org.id, user_id=other_owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_product)
    db.close()
    return owner, reviewer, outsider, other_owner, org, brand, product, other_org, other_brand, other_product


def test_manager_can_create_list_and_get_media_assets_with_scope_validation(client):
    owner, reviewer, _, _, org, brand, product, _, _, _ = seed_media_asset_fixture()

    create_response = client.post(
        '/api/v1/media-assets',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'scope': 'product',
            'name': 'Hero image',
            'description': 'Primary hero image for the starter kit.',
            'asset_key': 'organizations/media162/brands/rocket-tea/products/starter-kit/hero.png',
            'source_url': 'https://example.com/hero.png',
            'content_type': 'image/png',
            'size_bytes': 12345,
            'checksum': 'etag-123',
        },
        headers=auth_headers(client, owner.email),
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['product_id'] == str(product.id)
    assert created['scope'] == 'product'
    assert created['asset_key'].endswith('hero.png')

    list_response = client.get(
        f'/api/v1/media-assets?organization_id={org.id}&brand_id={brand.id}&scope=product&product_id={product.id}',
        headers=auth_headers(client, reviewer.email),
    )

    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']

    get_response = client.get(f"/api/v1/media-assets/{created['id']}", headers=auth_headers(client, reviewer.email))

    assert get_response.status_code == 200
    fetched = get_response.json()
    assert fetched['id'] == created['id']
    assert fetched['scope'] == 'product'


def test_cannot_create_media_asset_without_product_id_for_product_scope(client):
    owner, _, _, _, org, brand, _, _, _, _ = seed_media_asset_fixture()

    response = client.post(
        '/api/v1/media-assets',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'scope': 'product',
            'name': 'Broken asset',
            'description': 'Missing product id should fail.',
            'asset_key': 'organizations/media162/brands/rocket-tea/products/missing/hero.png',
            'content_type': 'image/png',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 422
    assert 'product_id is required when scope is product' in response.text


def test_cannot_create_media_asset_when_product_does_not_belong_to_brand(client):
    owner, _, _, _, org, brand, _, _, other_brand, other_product = seed_media_asset_fixture()

    response = client.post(
        '/api/v1/media-assets',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(other_product.id),
            'scope': 'product',
            'name': 'Mismatch asset',
            'description': 'This should fail because the product belongs elsewhere.',
            'asset_key': 'organizations/media162/brands/rocket-tea/products/mismatch/hero.png',
            'content_type': 'image/png',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Product does not belong to organization and brand'


def test_archived_organization_blocks_media_asset_create(client):
    owner, _, _, _, org, brand, _, _, _, _ = seed_media_asset_fixture(archived=True)

    response = client.post(
        '/api/v1/media-assets',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'scope': 'brand',
            'name': 'Frozen asset',
            'description': 'Should not be writable while org is archived.',
            'asset_key': 'organizations/media162/brands/rocket-tea/brand/banner.png',
            'content_type': 'image/png',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_outsider_cannot_list_media_assets_for_inaccessible_organization(client):
    owner, _, outsider, _, org, brand, product, _, _, _ = seed_media_asset_fixture()

    create_response = client.post(
        '/api/v1/media-assets',
        json={
            'organization_id': str(org.id),
            'brand_id': str(brand.id),
            'product_id': str(product.id),
            'scope': 'product',
            'name': 'Visible asset',
            'description': 'Outsider should not see this.',
            'asset_key': 'organizations/media162/brands/rocket-tea/products/starter-kit/visible.png',
            'content_type': 'image/png',
        },
        headers=auth_headers(client, owner.email),
    )
    assert create_response.status_code == 201

    response = client.get(
        f'/api/v1/media-assets?organization_id={org.id}&brand_id={brand.id}',
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403
    assert response.json()['detail'] == 'No access to organization'
