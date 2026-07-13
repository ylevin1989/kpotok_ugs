from datetime import date

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ID = 'worker-p208'


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


def worker_headers() -> dict[str, str]:
    return {'X-Worker-Token': settings.worker_token, 'X-Worker-Id': WORKER_ID}


def seed_content_generation_fixture():
    owner = seed_user('owner-p208@example.com')
    manager = seed_user('manager-p208@example.com')
    reviewer = seed_user('reviewer-p208@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet208', slug='uno-packet208', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea 208',
        slug='rocket-tea-p208',
        dna_json={
            'positioning': 'clear and practical',
            'tone_of_voice': ['clear', 'practical', 'energetic'],
            'allowed_claims': ['Fast setup', 'Low friction'],
            'forbidden_claims': ['Guaranteed results'],
        },
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-208-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for content generation regression.',
        features=['Fast setup'],
        benefits=['Launch faster'],
        proofs=['Used by early adopters'],
        objections=['Too much work'],
        restrictions=['Avoid absolute claims'],
        dna_json={'positioning': 'starter'},
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
    plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=audience_segment.id,
        scope='product',
        date=date(2026, 7, 5),
        title='Rocket Tea launch week',
        platform='instagram',
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
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        title='Launch social post',
        status='draft',
        quality_score=0,
    )
    db.add(item)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    org_id = str(org.id)
    brand_id = str(brand.id)
    content_item_id = str(item.id)
    db.close()
    return owner, manager, reviewer, org_id, brand_id, content_item_id


def test_content_generation_completion_persists_structured_json_and_body_markdown(client):
    owner, manager, reviewer, org_id, brand_id, content_item_id = seed_content_generation_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item_id}/generate',
        headers=auth_headers(client, manager.email),
    )
    assert response.status_code == 201
    job = response.json()

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    payload = {
        'title': 'Rocket Tea launch post',
        'text': 'Use the starter kit to launch faster without wasting time.',
        'short_text': 'Launch faster with less friction.',
        'cta': 'Get the starter kit',
        'visual_task': 'Show a focused founder preparing a fast launch.',
        'image_prompt': 'A clean launch-day scene with a practical starter kit on a desk.',
        'risks': ['Avoid guaranteed outcomes', 'Keep the claim within supported facts'],
        'body_markdown': '# Rocket Tea launch post\n\nUse the starter kit to launch faster without wasting time.',
    }

    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': __import__('json').dumps(payload)},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    versions_response = client.get(
        f'/api/v1/content-versions?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()['items']
    assert len(versions) == 1
    assert versions[0]['body_markdown'] == payload['body_markdown']
    assert versions[0]['structured_json'] == {k: v for k, v in payload.items() if k != 'body_markdown'}
    assert versions[0]['generation_type'] == 'initial'
