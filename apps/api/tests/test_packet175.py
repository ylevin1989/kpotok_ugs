from datetime import date

from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
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


def seed_paused_content_item_fixture():
    owner = seed_user('owner-p175@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet175', slug='uno-packet175', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 175', slug='rocket-tea-p175')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-175-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for paused content-item regression.',
    )
    db.add(product)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        name='Busy decision-maker',
        description='Needs fast proof and low-friction onboarding.',
        pain_points=['Not enough time'],
        goals=['Move fast'],
        objections=['Too complex'],
        keywords=['quick setup'],
    )
    db.add(audience_segment)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea QA week 175',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_plan)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(audience_segment)
    db.refresh(content_plan)
    org_id = str(org.id)
    brand_id = str(brand.id)
    product_id = str(product.id)
    content_plan_id = str(content_plan.id)
    audience_segment_id = str(audience_segment.id)
    db.close()
    return owner, org_id, brand_id, product_id, content_plan_id, audience_segment_id


def test_paused_organization_blocks_content_item_creation(client):
    owner, org_id, brand_id, product_id, content_plan_id, audience_segment_id = seed_paused_content_item_fixture()

    paused = client.patch(
        f'/api/v1/organizations/{org_id}',
        json={'status': 'paused'},
        headers=auth_headers(client, owner.email),
    )
    assert paused.status_code == 200
    assert paused.json()['status'] == 'paused'

    response = client.post(
        '/api/v1/content-items',
        json={
            'organization_id': org_id,
            'brand_id': brand_id,
            'product_id': product_id,
            'content_plan_id': content_plan_id,
            'audience_segment_id': audience_segment_id,
            'scope': 'product',
            'platform': 'instagram',
            'content_type': 'post',
            'goal': 'Drive launch awareness',
            'title': 'Paused content item should fail',
            'status': 'draft',
            'quality_score': 88,
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Paused organization is read-only for content writes'
