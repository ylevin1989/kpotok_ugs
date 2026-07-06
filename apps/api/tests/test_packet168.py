from datetime import date

from app.core.security import hash_password
from app.db.enums import GenerationType
from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_plan import ContentPlan
from app.db.models.content_version import ContentVersion
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.ticket import Ticket
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


def seed_quality_check_fixture(archived: bool = False):
    owner = seed_user('owner-p168@example.com')
    reviewer = seed_user('reviewer-p168@example.com')
    outsider = seed_user('outsider-p168@example.com')
    db = SessionLocal()
    org = Organization(
        name='Uno Packet168',
        slug='uno-packet168',
        status=OrganizationStatus.ARCHIVED if archived else OrganizationStatus.ACTIVE,
    )
    db.add(org)
    db.flush()
    brand = Brand(
        organization_id=org.id,
        name='Rocket Tea',
        slug='rocket-tea-p168',
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
        sku='SKU-168-001',
        name='Rocket Tea Starter Kit',
        category='starter-kit',
        description='Starter kit for quality checks.',
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
        date=date(2026, 7, 5),
        title='Rocket Tea QA week',
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
        title='QA post',
        content_type='post',
        platform='instagram',
        goal='Drive launch awareness',
        status='draft',
        quality_score=42,
    )
    db.add(content_item)
    db.flush()
    version = ContentVersion(
        organization_id=org.id,
        content_item_id=content_item.id,
        version_number=1,
        body_markdown=(
            '# Rocket Tea launch note\n\n'
            'Rocket Tea Starter Kit is a clear, practical tea kit for smooth focus.\n\n'
            'This starter kit includes cold brew concentrate, single-origin tea, and a caffeine-rich blend with lab-tested proof.\n\n'
            'The tone stays clear, practical, and energetic with no bitter aftertaste.'
        ),
        structured_json={
            'hook': 'Smooth focus without bitter aftertaste',
            'proof': 'lab-tested proof',
            'audience': 'busy founders',
            'cta': 'Try the starter kit',
        },
        change_summary='Initial draft',
        generation_type=GenerationType.INITIAL,
        generated_from_task_id=None,
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
        type='revision_request',
        reason_codes=['needs_clarity'],
        comment='Needs sharper CTA.',
        status='open',
        priority='normal',
        assigned_agent_role='content_creator',
        created_by_id=reviewer.id,
        resolved_at=None,
    )
    db.add(ticket)
    other_org = Organization(name='Other Packet168', slug='other-packet168', status=OrganizationStatus.ACTIVE)
    db.add(other_org)
    db.flush()
    other_brand = Brand(organization_id=other_org.id, name='Other Brand', slug='other-brand-p168')
    db.add(other_brand)
    db.flush()
    other_product = Product(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        sku='SKU-168-OTHER',
        name='Other Starter Kit',
        category='starter-kit',
        description='Belongs to another organization.',
    )
    db.add(other_product)
    db.flush()
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    db.refresh(org)
    db.refresh(brand)
    db.refresh(product)
    db.refresh(content_plan)
    db.refresh(content_item)
    db.refresh(version)
    db.refresh(ticket)
    db.refresh(other_org)
    db.refresh(other_brand)
    db.refresh(other_product)
    db.close()
    return owner, reviewer, outsider, org, brand, product, content_plan, content_item, version, ticket, other_org, other_brand, other_product


def test_manager_can_create_list_and_get_quality_checks_with_ticket_default(client):
    owner, reviewer, _, org, brand, product, _, content_item, version, ticket, _, _, _ = seed_quality_check_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'ticket_id': str(ticket.id),
            'summary': 'Run the automatic quality gate.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    created = response.json()
    assert created['organization_id'] == str(org.id)
    assert created['brand_id'] == str(brand.id)
    assert created['product_id'] == str(product.id)
    assert created['content_item_id'] == str(content_item.id)
    assert created['content_version_id'] == str(version.id)
    assert created['ticket_id'] == str(ticket.id)
    assert created['status'] == 'passed'
    assert created['score'] >= 80
    assert created['checks_json']['product_accuracy_score'] >= 90
    assert created['checks_json']['risk_score'] <= 30

    item_response = client.get(f'/api/v1/content-items/{content_item.id}', headers=auth_headers(client, reviewer.email))
    assert item_response.status_code == 200
    assert item_response.json()['quality_score'] == created['score']
    assert item_response.json()['status'] == 'waiting_client_review'

    list_response = client.get(
        f'/api/v1/quality-checks?organization_id={org.id}&content_item_id={content_item.id}',
        headers=auth_headers(client, reviewer.email),
    )
    assert list_response.status_code == 200
    items = list_response.json()['items']
    assert len(items) == 1
    assert items[0]['id'] == created['id']

    get_response = client.get(f"/api/v1/quality-checks/{created['id']}", headers=auth_headers(client, reviewer.email))
    assert get_response.status_code == 200
    assert get_response.json()['id'] == created['id']


def test_quality_check_defaults_to_current_content_version_when_not_provided(client):
    owner, _, _, org, _, _, _, content_item, version, _, _, _, _ = seed_quality_check_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'summary': 'Use the current content version.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 201
    created = response.json()
    assert created['content_version_id'] == str(version.id)
    assert created['ticket_id'] is None
    assert created['status'] == 'passed'
    assert created['score'] >= 80


def test_outsider_cannot_create_quality_check(client):
    _, _, outsider, org, _, _, _, content_item, _, _, _, _, _ = seed_quality_check_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'summary': 'Attempted by outsider.',
        },
        headers=auth_headers(client, outsider.email),
    )

    assert response.status_code == 403


def test_archived_organization_blocks_quality_check_create(client):
    owner, _, _, org, _, _, _, content_item, _, _, _, _, _ = seed_quality_check_fixture(archived=True)

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'summary': 'Archived org should stay read-only.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert response.status_code == 409
    assert response.json()['detail'] == 'Archived organization is read-only'


def test_quality_check_rejects_cross_scope_ticket_and_version(client):
    owner, _, _, org, _, _, _, content_item, _, ticket, other_org, other_brand, _ = seed_quality_check_fixture()

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'ticket_id': str(ticket.id),
            'content_version_id': str(content_item.current_version_id),
            'summary': 'Sanity check.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert response.status_code == 201

    other_db = SessionLocal()
    other_ticket = Ticket(
        organization_id=other_org.id,
        brand_id=other_brand.id,
        product_id=None,
        content_item_id=content_item.id,
        content_version_id=content_item.current_version_id,
        type='revision_request',
        reason_codes=['other'],
        comment='Other org ticket',
        status='open',
        priority='normal',
        assigned_agent_role='content_creator',
        created_by_id=None,
        resolved_at=None,
    )
    other_db.add(other_ticket)
    other_db.commit()
    other_db.refresh(other_ticket)
    other_db.close()

    conflict = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'ticket_id': str(other_ticket.id),
            'summary': 'Should fail cross-scope validation.',
        },
        headers=auth_headers(client, owner.email),
    )

    assert conflict.status_code == 409
    assert conflict.json()['detail'] == 'Ticket does not belong to content item and organization'


def test_quality_check_fails_for_low_quality_current_version_and_gates_internal_review(client):
    owner, _, _, org, _, product, _, content_item, _, _, _, _, _ = seed_quality_check_fixture()

    version_response = client.post(
        '/api/v1/content-versions',
        json={
            'organization_id': str(org.id),
            'content_item_id': str(content_item.id),
            'version_number': 2,
            'body_markdown': '# Generic hype\n\nUnbelievable results guaranteed. Best tea ever. Instant results and no risk.',
            'structured_json': {'headline': 'Generic hype'},
            'change_summary': 'Low quality revision',
            'generation_type': 'revision',
            'generated_from_task_id': None,
            'is_current': True,
        },
        headers=auth_headers(client, owner.email),
    )
    assert version_response.status_code == 201

    response = client.post(
        f'/api/v1/content-items/{content_item.id}/quality-check',
        json={
            'organization_id': str(org.id),
            'summary': 'Gate the weak version automatically.',
        },
        headers=auth_headers(client, owner.email),
    )
    assert response.status_code == 201
    created = response.json()
    assert created['product_id'] == str(product.id)
    assert created['status'] in {'needs_revision', 'failed'}
    assert created['score'] < 80 or created['checks_json']['product_accuracy_score'] < 90 or created['checks_json']['risk_score'] > 30

    item_response = client.get(f"/api/v1/content-items/{content_item.id}", headers=auth_headers(client, owner.email))
    assert item_response.status_code == 200
    assert item_response.json()['status'] == 'internal_review'
