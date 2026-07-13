from datetime import date
import json

from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership
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


def seed_rich_generation_fixture():
    owner = seed_user('owner-p206@example.com')
    manager = seed_user('manager-p206@example.com')

    db = SessionLocal()
    org = Organization(name='Packet206 Org', slug='packet206-org')
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea 206',
        slug='rocket-tea-p206',
        dna_json={'voice': 'bold', 'values': ['clarity', 'speed']},
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='p206-sku-a',
        name='Rocket Tea Kit A',
        category='starter-kit',
        description='Selected product for packet 206',
        features=['Fast setup', 'Reusable templates'],
        benefits=['Launch faster'],
        proofs=['Used by early adopters'],
        objections=['Too much work'],
        restrictions=['Do not mention beta pricing'],
        dna_json={'positioning': 'starter'},
    )
    db.add(product)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        name='Busy founder',
        description='Wants quick proof without noise.',
        pain_points=['No time to explore long docs'],
        goals=['Get to value quickly'],
        objections=['Implementation risk'],
        keywords=['quick start', 'fast proof'],
    )
    db.add(audience_segment)
    db.flush()
    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Packet206 launch plan',
        platform='telegram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(plan)
    db.flush()
    item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=plan.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        platform='telegram',
        content_type='post',
        goal='Drive launch awareness',
        title='Packet206 launch post',
        status='draft',
        quality_score=0,
    )
    db.add(item)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(audience_segment)
    db.refresh(plan)
    db.refresh(item)
    payload = {
        'owner_email': owner.email,
        'manager_email': manager.email,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'product_id': str(product.id),
        'audience_segment_id': str(audience_segment.id),
        'content_plan_id': str(plan.id),
        'content_item_id': str(item.id),
    }
    db.close()
    return payload


def seed_product_scope_mismatch_fixture():
    owner = seed_user('owner-p206-mismatch@example.com')
    manager = seed_user('manager-p206-mismatch@example.com')

    db = SessionLocal()
    org = Organization(name='Packet206 Mismatch Org', slug='packet206-mismatch-org')
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Packet206 Mismatch Brand', slug='packet206-mismatch-brand')
    db.add(brand)
    db.flush()
    product_a = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='p206-sku-a-mismatch',
        name='Selected Product A',
        category='starter-kit',
        description='Selected product',
        features=['A feature'],
        benefits=['A benefit'],
        proofs=['A proof'],
        objections=['A objection'],
        restrictions=['A restriction'],
    )
    db.add(product_a)
    db.flush()
    product_b = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='p206-sku-b-mismatch',
        name='Wrong Product B',
        category='starter-kit',
        description='Wrong product',
        features=['B feature'],
        benefits=['B benefit'],
        proofs=['B proof'],
        objections=['B objection'],
        restrictions=['B restriction'],
    )
    db.add(product_b)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product_a.id,
        scope='product',
        name='Mismatch audience',
        description='Audience stays on the selected product.',
        pain_points=['Pain'],
        goals=['Goal'],
        objections=['Objection'],
        keywords=['keyword'],
    )
    db.add(audience_segment)
    db.flush()
    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product_b.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Packet206 mismatch plan',
        platform='telegram',
        content_type='post',
        goal='Wrong product scope',
        status='draft',
    )
    db.add(plan)
    db.flush()
    item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product_a.id,
        content_plan_id=plan.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        platform='telegram',
        content_type='post',
        goal='Wrong product scope',
        title='Packet206 mismatch post',
        status='draft',
        quality_score=0,
    )
    db.add(item)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(plan)
    db.refresh(item)
    payload = {
        'manager_email': manager.email,
        'content_item_id': str(item.id),
    }
    db.close()
    return payload


def test_generate_content_item_brief_embeds_rich_context_and_scope_specific_product(client):
    fixture = seed_rich_generation_fixture()

    response = client.post(
        f"/api/v1/content-items/{fixture['content_item_id']}/generate",
        headers=auth_headers(client, fixture['manager_email']),
    )

    assert response.status_code == 201
    job = response.json()
    assert job['brief_content'] is not None
    brief_response = client.get(
        f"/api/v1/briefs/{job['brief_id']}",
        headers=auth_headers(client, fixture['owner_email']),
    )
    assert brief_response.status_code == 200
    brief = brief_response.json()
    payload = json.loads(brief['content'])

    assert payload['kind'] == 'content_item_generation'
    assert payload['organization_id'] == fixture['organization_id']
    assert payload['brand_id'] == fixture['brand_id']
    assert payload['brand_context'] == {
        'id': fixture['brand_id'],
        'name': 'Rocket Tea 206',
        'dna_json': {'voice': 'bold', 'values': ['clarity', 'speed']},
    }
    assert payload['product_context']['id'] == fixture['product_id']
    assert payload['product_context']['name'] == 'Rocket Tea Kit A'
    assert payload['product_context']['features'] == ['Fast setup', 'Reusable templates']
    assert payload['product_context']['dna_json'] == {'positioning': 'starter'}
    assert payload['audience_context']['id'] == fixture['audience_segment_id']
    assert payload['audience_context']['name'] == 'Busy founder'
    assert payload['channel'] == {
        'goal': 'Drive launch awareness',
        'platform': 'telegram',
        'date': '2026-07-05',
    }
    assert payload['task'] == {
        'platform': 'telegram',
        'content_type': 'post',
        'goal': 'Drive launch awareness',
        'title': 'Packet206 launch post',
        'scope': 'product',
    }


def test_generate_content_item_brief_rejects_mismatched_product_scope(client):
    fixture = seed_product_scope_mismatch_fixture()

    response = client.post(
        f"/api/v1/content-items/{fixture['content_item_id']}/generate",
        headers=auth_headers(client, fixture['manager_email']),
    )

    assert response.status_code == 409
    assert 'Content plan product does not match content item product scope' in response.json()['detail']
