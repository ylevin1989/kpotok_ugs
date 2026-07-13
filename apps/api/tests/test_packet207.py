from datetime import date
from uuid import UUID

from app.core.security import hash_password
from app.db.models.audience_segment import AudienceSegment
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.job import Job
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal


WORKER_TOKEN = 'packet23-worker-token'
WORKER_ALPHA = 'worker-alpha'


def _seed_user(email: str, password: str = 'test12345') -> User:
    db = SessionLocal()
    user = User(email=email, password_hash=hash_password(password), is_active=True)
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _auth_headers(client, email: str, password: str = 'test12345') -> dict[str, str]:
    response = client.post('/api/v1/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return {'Authorization': f"Bearer {response.json()['access_token']}"}


def _worker_headers() -> dict[str, str]:
    return {'X-Worker-Token': WORKER_TOKEN, 'X-Worker-Id': WORKER_ALPHA}


def _seed_generation_context_fixture():
    owner = _seed_user('owner-p207@example.com')
    manager = _seed_user('manager-p207@example.com')

    db = SessionLocal()
    org = Organization(name='Packet207 Org', slug='packet207-org')
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Packet207 Brand',
        slug='packet207-brand',
        dna_json={'voice': 'bold'},
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='packet207-sku',
        name='Packet207 Kit',
        category='starter-kit',
        description='Kit for claim-time context propagation',
        features=['Fast setup'],
        benefits=['Launch faster'],
        proofs=['Used by early adopters'],
        objections=['Too much work'],
        restrictions=['Avoid beta pricing'],
        dna_json={'positioning': 'starter'},
    )
    db.add(product)
    db.flush()
    audience_segment = AudienceSegment(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        scope='product',
        name='Packet207 audience',
        description='Needs practical launch proof.',
        pain_points=['No time'],
        goals=['Quick clarity'],
        objections=['Implementation risk'],
        keywords=['quick start'],
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
        title='Packet207 plan',
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
        title='Packet207 launch post',
        status='draft',
        quality_score=0,
    )
    db.add(item)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.commit()
    db.refresh(item)

    return {
        'owner_email': owner.email,
        'manager_email': manager.email,
        'organization_id': str(org.id),
        'brand_id': str(brand.id),
        'product_id': str(product.id),
        'audience_segment_id': str(audience_segment.id),
        'content_plan_id': str(plan.id),
        'content_item_id': str(item.id),
    }


def _seed_followup_job(brief_id, organization_id, brand_id) -> str:
    db = SessionLocal()
    job = Job(
        organization_id=UUID(organization_id),
        brand_id=UUID(brand_id),
        brief_id=UUID(brief_id),
        title='Packet207 follow-up job',
        status='queued',
        kind='manual',
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = str(job.id)
    db.close()
    return job_id


def test_claim_next_job_returns_generation_context(client):
    fixture = _seed_generation_context_fixture()

    generate_response = client.post(
        f"/api/v1/content-items/{fixture['content_item_id']}/generate",
        headers=_auth_headers(client, fixture['manager_email']),
    )
    assert generate_response.status_code == 201
    generated_job = generate_response.json()
    assert generated_job['context']['task']['title'] == 'Packet207 launch post'

    claim_response = client.post('/api/v1/jobs/claim-next', headers=_worker_headers())
    assert claim_response.status_code == 200
    claimed_job = claim_response.json()
    assert claimed_job['context']['kind'] == 'content_item_generation'
    assert claimed_job['context']['brand_context']['name'] == 'Packet207 Brand'
    assert claimed_job['context']['task']['scope'] == 'product'
    assert claimed_job['brief_content'] is not None


def test_claim_job_returns_generation_context(client):
    fixture = _seed_generation_context_fixture()

    generate_response = client.post(
        f"/api/v1/content-items/{fixture['content_item_id']}/generate",
        headers=_auth_headers(client, fixture['manager_email']),
    )
    assert generate_response.status_code == 201
    brief_id = generate_response.json()['brief_id']
    followup_job_id = _seed_followup_job(brief_id, fixture['organization_id'], fixture['brand_id'])

    claim_response = client.post(f'/api/v1/jobs/{followup_job_id}/claim', headers=_worker_headers())
    assert claim_response.status_code == 200
    claimed_job = claim_response.json()
    assert claimed_job['context']['task']['title'] == 'Packet207 launch post'
    assert claimed_job['context']['channel']['platform'] == 'telegram'
    assert claimed_job['brief_content'] is not None
