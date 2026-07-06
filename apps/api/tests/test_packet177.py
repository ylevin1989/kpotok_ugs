import json

from app.core.config import settings
from app.core.security import hash_password
from app.db.models.brand import Brand
from app.db.models.organization import MembershipRole, Organization, OrganizationMembership, OrganizationStatus
from app.db.models.product import Product
from app.db.models.user import User
from app.db.session import SessionLocal

WORKER_ID = 'worker-p177'


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


def seed_brand_product_fixture():
    owner = seed_user('owner-p177@example.com')
    manager = seed_user('manager-p177@example.com')
    reviewer = seed_user('reviewer-p177@example.com')
    db = SessionLocal()
    org = Organization(name='Uno Packet177', slug='uno-packet177', status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    brand = Brand(organization_id=org.id, name='Rocket Tea 177', slug='rocket-tea-p177')
    db.add(brand)
    db.flush()
    product = Product(
        organization_id=org.id,
        brand_id=brand.id,
        sku='SKU-177-001',
        name='Rocket Tea Focus Pack',
        category='focus-pack',
        description='Focus pack for brand/product DNA regression.',
        features=['Fast setup', 'Low friction'],
        benefits=['Gets teams moving'],
        proofs=['Adopted by early teams'],
        objections=['Too much setup'],
        restrictions=['No regulated claims'],
    )
    db.add(product)
    db.add(OrganizationMembership(organization_id=org.id, user_id=owner.id, role=MembershipRole.CLIENT_OWNER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=manager.id, role=MembershipRole.CLIENT_MANAGER))
    db.add(OrganizationMembership(organization_id=org.id, user_id=reviewer.id, role=MembershipRole.CLIENT_REVIEWER))
    db.commit()
    brand_id = str(brand.id)
    product_id = str(product.id)
    org_id = str(org.id)
    db.close()
    return owner, manager, reviewer, org_id, brand_id, product_id


def test_generate_brand_dna_creates_job_and_persists_dna(client):
    owner, manager, reviewer, org_id, brand_id, product_id = seed_brand_product_fixture()

    response = client.post(
        f'/api/v1/brands/{brand_id}/generate-dna',
        headers=auth_headers(client, manager.email),
    )
    assert response.status_code == 201
    job = response.json()
    assert job['organization_id'] == org_id
    assert job['brand_id'] == brand_id
    assert job['title'] == 'Generate brand DNA: Rocket Tea 177'
    assert job['status'] == 'queued'

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    dna_payload = {
        'positioning': 'Fast, practical, and clear',
        'tone_of_voice': 'confident and direct',
        'allowed_claims': ['Fast setup', 'Low friction'],
        'forbidden_claims': ['Guaranteed results'],
        'content_rules': ['Be concrete', 'Avoid hype'],
    }
    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': json.dumps(dna_payload)},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    brand_response = client.get(f'/api/v1/brands/{brand_id}', headers=auth_headers(client, reviewer.email))
    assert brand_response.status_code == 200
    brand = brand_response.json()
    assert brand['dna_json']['kind'] == 'brand_dna_generation'
    assert brand['dna_json']['dna'] == dna_payload
    assert brand['dna_json']['source_job_id'] == job['id']


def test_generate_product_dna_creates_job_and_persists_dna(client):
    owner, manager, reviewer, org_id, brand_id, product_id = seed_brand_product_fixture()

    response = client.post(
        f'/api/v1/products/{product_id}/generate-dna',
        headers=auth_headers(client, manager.email),
    )
    assert response.status_code == 201
    job = response.json()
    assert job['organization_id'] == org_id
    assert job['brand_id'] == brand_id
    assert job['title'] == 'Generate product DNA: Rocket Tea Focus Pack'
    assert job['status'] == 'queued'

    claim_response = client.post('/api/v1/jobs/claim-next', headers=worker_headers())
    assert claim_response.status_code == 200
    assert claim_response.json()['id'] == job['id']

    dna_payload = {
        'summary': 'A focus pack for practical teams',
        'features': ['Fast setup', 'Low friction'],
        'benefits': ['Gets teams moving'],
        'proofs': ['Adopted by early teams'],
        'objections': ['Too much setup'],
        'content_angles': ['Speed', 'Clarity'],
    }
    complete_response = client.post(
        f"/api/v1/jobs/{job['id']}/complete",
        json={'output_text': json.dumps(dna_payload)},
        headers=worker_headers(),
    )
    assert complete_response.status_code == 200

    product_response = client.get(f'/api/v1/products/{product_id}', headers=auth_headers(client, reviewer.email))
    assert product_response.status_code == 200
    product = product_response.json()
    assert product['dna_json']['kind'] == 'product_dna_generation'
    assert product['dna_json']['dna'] == dna_payload
    assert product['dna_json']['source_job_id'] == job['id']
