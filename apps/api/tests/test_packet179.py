from datetime import date

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ID = 'worker-p179'


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


def seed_generation_fixture():
    owner = seed_user('owner-p179@example.com')
    reviewer = seed_user('reviewer-p179@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet179', slug='uno-packet179', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea',
        slug='rocket-tea-p179',
        dna_json={
            'positioning': 'clear, practical tea for focused days',
            'tone_of_voice': ['clear', 'practical', 'energetic'],
            'content_rules': ['avoid hype', 'avoid miracle claims'],
        },
    )
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-179-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for generation gating.',
        features=['cold brew concentrate', 'single-origin tea', 'smooth focus'],
        benefits=['calm energy', 'no bitter aftertaste'],
        proofs=['lab-tested proof'],
        objections=['too bitter'],
        restrictions=['contains caffeine'],
        dna_json={
            'summary': 'A starter kit for smooth focus without bitterness.',
            'content_angles': ['focus without crash', 'calm energy for busy founders'],
        },
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
        title='Rocket Tea launch week',
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
        title='Launch note',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
        quality_score=0,
    )
    db.add(content_item)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    content_item_id = str(content_item.id)
    org_id = str(org.id)
    db.close()
    return owner, reviewer, org_id, content_item_id


def _run_generation(client, owner_email: str, content_item_id: str, output_text: str) -> None:
    generate_response = client.post(
        f'/api/v1/content-items/{content_item_id}/generate',
        headers=auth_headers(client, owner_email),
    )
    assert generate_response.status_code == 201
    job = generate_response.json()

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': output_text},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200


def test_auto_quality_check_passes_on_generated_content_and_releases_item_to_client_review(client):
    owner, reviewer, org_id, content_item_id = seed_generation_fixture()

    _run_generation(
        client,
        owner.email,
        content_item_id,
        '# Rocket Tea launch note\n\nRocket Tea Starter Kit delivers smooth focus with cold brew concentrate, single-origin tea, and lab-tested proof. Clear, practical, energetic messaging for busy founders.',
    )

    item_response = client.get(f'/api/v1/content-items/{content_item_id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    item = item_response.json()
    assert item['status'] == 'waiting_client_review'
    assert item['quality_score'] >= 80

    quality_response = client.get(
        f'/api/v1/quality-checks?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert quality_response.status_code == 200
    checks = quality_response.json()['items']
    assert len(checks) == 1
    assert checks[0]['status'] == 'passed'
    assert checks[0]['checks_json']['product_accuracy_score'] >= 90
    assert checks[0]['checks_json']['risk_score'] <= 30


def test_auto_quality_check_fails_on_risky_generated_content_and_gates_internal_review(client):
    owner, reviewer, org_id, content_item_id = seed_generation_fixture()

    _run_generation(
        client,
        owner.email,
        content_item_id,
        '# Launch note\n\nMiracle 100% guaranteed instant results. No risk. Best ever!',
    )

    item_response = client.get(f'/api/v1/content-items/{content_item_id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    item = item_response.json()
    assert item['status'] == 'internal_review'
    assert item['quality_score'] >= 80

    quality_response = client.get(
        f'/api/v1/quality-checks?organization_id={org_id}&content_item_id={content_item_id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert quality_response.status_code == 200
    checks = quality_response.json()['items']
    assert len(checks) == 1
    assert checks[0]['status'] in {'needs_revision', 'failed'}
    assert checks[0]['checks_json']['risk_score'] > 30
    assert checks[0]['checks_json']['product_accuracy_score'] >= 90
