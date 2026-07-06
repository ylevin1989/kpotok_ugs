from datetime import date

from app.core.config import settings
from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ID = 'worker-p178'


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


def seed_revision_fixture():
    owner = seed_user('owner-p178@example.com')
    reviewer = seed_user('reviewer-p178@example.com')
    outsider = seed_user('outsider-p178@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet178', slug='uno-packet178', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 178', slug='rocket-tea-p178')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-178-001',
        name='Rocket Tea Revision Pack',
        category='revision-pack',
        description='Revision pack for ticket processing regression.',
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
        title='Rocket Tea revision week',
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
        title='Revision post',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown='# Revision post\n\nInitial draft body.',
        structured_json={'headline': 'Initial draft body'},
        change_summary='Initial draft',
        generation_type=GenerationType.INITIAL,
        generated_from_task_id=None,
        created_by=owner.id,
        is_current=True,
    )
    db.add(version)
    db.flush()
    content_item.current_version_id = version.id
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    org_id = str(org.id)
    content_item_id = str(content_item.id)
    version_id = str(version.id)
    db.close()
    return owner, reviewer, outsider, org_id, content_item_id, version_id


def test_process_revision_ticket_creates_new_content_version(client):
    owner, reviewer, outsider, org_id, content_item_id, version_id = seed_revision_fixture()

    revision_response = client.post(
        f'/api/v1/content-items/{content_item_id}/request-revision',
        json={
            'reason_codes': ['missing_proof', 'too_generic'],
            'comment': 'Please tighten the proof and tailor the angle.',
            'priority': 'high',
            'assigned_agent_role': 'content_creator',
        },
        headers=auth_headers(client, owner.email),
    )
    assert revision_response.status_code == 201
    ticket = revision_response.json()
    assert ticket['type'] == 'revision_request'
    assert ticket['status'] == 'open'
    assert ticket['content_version_id'] == version_id

    process_response = client.post(
        f"/api/v1/tickets/{ticket['id']}/process",
        headers=auth_headers(client, owner.email),
    )
    assert process_response.status_code == 201
    job = process_response.json()
    assert job['organization_id'] == org_id
    assert job['status'] == 'queued'
    assert job['title'] == 'Process ticket: Revision post'

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    revised_body = '# Revision post\n\nRewritten after ticket processing.'
    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': revised_body},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    item_response = client.get(f'/api/v1/content-items/{content_item_id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    item = item_response.json()
    assert item['status'] == 'internal_review'
    assert item['current_version_id'] != version_id
    assert item['quality_score'] < 80

    versions_response = client.get(
        f'/api/v1/content-versions?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert versions_response.status_code == 200
    versions = versions_response.json()['items']
    assert len(versions) == 2
    assert versions[1]['version_number'] == 2
    assert versions[1]['generation_type'] == 'revision'
    assert versions[1]['body_markdown'] == revised_body
    assert versions[1]['is_current'] is True
    assert versions[1]['generated_from_task_id'] == job['id']

    quality_response = client.get(
        f'/api/v1/quality-checks?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert quality_response.status_code == 200
    checks = quality_response.json()['items']
    assert len(checks) == 1
    assert checks[0]['ticket_id'] == ticket['id']
    assert checks[0]['status'] in {'needs_revision', 'failed'}

    ticket_response = client.get(f"/api/v1/tickets/{ticket['id']}", headers=auth_headers(client, owner.email))
    assert ticket_response.status_code == 200
    resolved_ticket = ticket_response.json()
    assert resolved_ticket['status'] == 'resolved'
    assert resolved_ticket['resolved_at'] is not None


def test_outsider_cannot_process_ticket(client):
    owner, reviewer, outsider, org_id, content_item_id, version_id = seed_revision_fixture()

    revision_response = client.post(
        f'/api/v1/content-items/{content_item_id}/request-revision',
        json={'reason_codes': ['missing_proof']},
        headers=auth_headers(client, owner.email),
    )
    assert revision_response.status_code == 201
    ticket = revision_response.json()

    process_response = client.post(
        f"/api/v1/tickets/{ticket['id']}/process",
        headers=auth_headers(client, outsider.email),
    )
    assert process_response.status_code == 403
