import json
from datetime import date
from uuid import UUID

from app.core.config import settings
from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brief import Brief
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.ticket import Ticket
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ID = 'worker-p198'


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


def seed_routing_fixture():
    owner = seed_user('owner-p198@example.com')
    manager = seed_user('manager-p198@example.com')
    reviewer = seed_user('reviewer-p198@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet198', slug='uno-packet198', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea 198',
        slug='rocket-tea-p198',
        dna_json={'positioning': 'fast confidence'},
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-198-001',
        name='Rocket Tea Focus Pack 198',
        category='focus-pack',
        description='Focus pack for routing regression.',
        features=['Fast setup'],
        benefits=['Gets teams moving'],
        proofs=['Adopted by early teams'],
        objections=['Too much setup'],
        restrictions=['No regulated claims'],
    )
    db.add(product)
    db.flush()
    content_plan = ContentPlan(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        audience_segment_id=None,
        scope='product',
        date=date(2026, 7, 6),
        title='Routing regression plan',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_plan)
    db.flush()
    content_item = ContentItem(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_plan_id=content_plan.id,
        current_version_id=None,
        scope='product',
        platform='instagram',
        content_type='post',
        goal='Drive launch awareness',
        title='Routing regression item',
        status='draft',
        quality_score=0,
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='Initial body',
        structured_json={'hello': 'world'},
        change_summary='Seed version',
        generation_type=GenerationType.INITIAL,
        created_by=owner.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    content_item.current_version_id = version.id
    ticket = Ticket(
        organization_id=org.id,
        brand_id=brand.id,
        product_id=product.id,
        content_item_id=content_item.id,
        content_version_id=version.id,
        type='revision',
        reason_codes=['clarity'],
        comment='Needs clearer wording',
        status='open',
        priority='normal',
        assigned_agent_role='content_creator',
        created_by_id=reviewer.id,
    )
    db.add(ticket)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    ids = {
        'org_id': str(org.id),
        'brand_id': str(brand.id),
        'product_id': str(product.id),
        'content_item_id': str(content_item.id),
        'content_plan_id': str(content_plan.id),
        'ticket_id': str(ticket.id),
        'version_id': str(version.id),
    }
    db.close()
    return owner, manager, reviewer, ids


def test_job_creation_exposes_explicit_kind_and_target_refs(client):
    owner, manager, reviewer, ids = seed_routing_fixture()

    content_job = client.post(
        f"/api/v1/content-items/{ids['content_item_id']}/generate",
        headers=auth_headers(client, manager.email),
    )
    assert content_job.status_code == 201
    content_payload = content_job.json()
    assert content_payload['kind'] == 'content_generation'
    assert content_payload['target_content_item_id'] == ids['content_item_id']
    assert content_payload['target_brand_id'] == ids['brand_id']
    assert content_payload['target_product_id'] == ids['product_id']
    assert content_payload['target_ticket_id'] is None

    brand_job = client.post(
        f"/api/v1/brands/{ids['brand_id']}/generate-dna",
        headers=auth_headers(client, manager.email),
    )
    assert brand_job.status_code == 201
    brand_payload = brand_job.json()
    assert brand_payload['kind'] == 'dna_generation'
    assert brand_payload['target_brand_id'] == ids['brand_id']
    assert brand_payload['target_product_id'] is None
    assert brand_payload['target_content_item_id'] is None
    assert brand_payload['target_ticket_id'] is None

    product_job = client.post(
        f"/api/v1/products/{ids['product_id']}/generate-dna",
        headers=auth_headers(client, manager.email),
    )
    assert product_job.status_code == 201
    product_payload = product_job.json()
    assert product_payload['kind'] == 'dna_generation'
    assert product_payload['target_product_id'] == ids['product_id']
    assert product_payload['target_brand_id'] == ids['brand_id']
    assert product_payload['target_content_item_id'] is None
    assert product_payload['target_ticket_id'] is None

    ticket_job = client.post(
        f"/api/v1/tickets/{ids['ticket_id']}/process",
        headers=auth_headers(client, manager.email),
    )
    assert ticket_job.status_code == 201
    ticket_payload = ticket_job.json()
    assert ticket_payload['kind'] == 'ticket_processing'
    assert ticket_payload['target_ticket_id'] == ids['ticket_id']
    assert ticket_payload['target_content_item_id'] == ids['content_item_id']
    assert ticket_payload['target_brand_id'] == ids['brand_id']
    assert ticket_payload['target_product_id'] == ids['product_id']


def tamper_brief(job_id: str, payload: str) -> None:
    db = SessionLocal()
    brief = db.get(Brief, UUID(job_id))
    assert brief is not None
    brief.content = payload
    db.commit()
    db.close()


def test_content_generation_completion_does_not_depend_on_brief_json_shape(client):
    owner, manager, reviewer, ids = seed_routing_fixture()

    response = client.post(
        f"/api/v1/content-items/{ids['content_item_id']}/generate",
        headers=auth_headers(client, manager.email),
    )
    assert response.status_code == 201
    job = response.json()

    db = SessionLocal()
    brief = db.get(Brief, UUID(job['brief_id']))
    assert brief is not None
    brief.content = 'not-json-anymore'
    db.commit()
    db.close()

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': '# Generated content\n\nFresh output still should route.'},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    db = SessionLocal()
    versions = db.query(ContentVersion).filter(ContentVersion.content_item_id == UUID(ids['content_item_id'])).all()
    item = db.get(ContentItem, UUID(ids['content_item_id']))
    db.close()
    assert len(versions) == 2
    assert item is not None
    assert item.current_version_id is not None


def test_dna_and_ticket_completion_does_not_depend_on_brief_json_shape(client):
    owner, manager, reviewer, ids = seed_routing_fixture()

    brand_response = client.post(
        f"/api/v1/brands/{ids['brand_id']}/generate-dna",
        headers=auth_headers(client, manager.email),
    )
    assert brand_response.status_code == 201
    brand_job = brand_response.json()

    product_response = client.post(
        f"/api/v1/products/{ids['product_id']}/generate-dna",
        headers=auth_headers(client, manager.email),
    )
    assert product_response.status_code == 201
    product_job = product_response.json()

    ticket_response = client.post(
        f"/api/v1/tickets/{ids['ticket_id']}/process",
        headers=auth_headers(client, manager.email),
    )
    assert ticket_response.status_code == 201
    ticket_job = ticket_response.json()

    db = SessionLocal()
    for job_id in [brand_job['brief_id'], product_job['brief_id'], ticket_job['brief_id']]:
        brief = db.get(Brief, UUID(job_id))
        assert brief is not None
        brief.content = '{"kind":"someone_else"}'
    db.commit()
    db.close()

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == brand_job['id']
    complete_response = client.post(
        f"/api/v1/jobs/{brand_job['id']}/complete",
        json={'output_text': json.dumps({'positioning': 'clear'})},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == product_job['id']
    complete_response = client.post(
        f"/api/v1/jobs/{product_job['id']}/complete",
        json={'output_text': json.dumps({'summary': 'clear'})},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == ticket_job['id']
    complete_response = client.post(
        f"/api/v1/jobs/{ticket_job['id']}/complete",
        json={'output_text': '# Revised content\n\nStill routed by kind.'},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    db = SessionLocal()
    brand = db.get(Brand, UUID(ids['brand_id']))
    product = db.get(Product, UUID(ids['product_id']))
    ticket = db.get(Ticket, UUID(ids['ticket_id']))
    versions = db.query(ContentVersion).filter(ContentVersion.content_item_id == UUID(ids['content_item_id'])).all()
    db.close()
    assert brand is not None and brand.dna_json is not None
    assert product is not None and product.dna_json is not None
    assert ticket is not None and ticket.status == 'resolved'
    assert len(versions) == 2
