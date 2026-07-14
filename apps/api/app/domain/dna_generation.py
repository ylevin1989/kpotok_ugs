from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from app.db.models.brand import Brand
from app.db.models.brief import Brief
from app.db.models.product import Product

BRAND_DNA_BRIEF_KIND = 'brand_dna_generation'
PRODUCT_DNA_BRIEF_KIND = 'product_dna_generation'
BRAND_DNA_JOB_PREFIX = 'Generate brand DNA: '
PRODUCT_DNA_JOB_PREFIX = 'Generate product DNA: '
BRAND_DNA_BRIEF_PREFIX = 'Brand DNA request: '
PRODUCT_DNA_BRIEF_PREFIX = 'Product DNA request: '


def build_brand_dna_request(brand: Brand) -> dict[str, Any]:
    return {
        'kind': BRAND_DNA_BRIEF_KIND,
        'brand_id': str(brand.id),
        'organization_id': str(brand.organization_id),
        'name': brand.name,
        'slug': brand.slug,
        'positioning': brand.positioning,
        'tone_of_voice': brand.tone_of_voice,
        'mission': brand.mission,
        'values': brand.values,
        'forbidden_claims': brand.forbidden_claims,
        'allowed_claims': brand.allowed_claims,
        'competitors': brand.competitors,
        'good_examples': brand.good_examples,
        'bad_examples': brand.bad_examples,
    }


def build_product_dna_request(product: Product) -> dict[str, Any]:
    return {
        'kind': PRODUCT_DNA_BRIEF_KIND,
        'product_id': str(product.id),
        'organization_id': str(product.organization_id),
        'brand_id': str(product.brand_id),
        'sku': product.sku,
        'name': product.name,
        'category': product.category,
        'description': product.description,
        'features': product.features,
        'benefits': product.benefits,
        'proofs': product.proofs,
        'objections': product.objections,
        'restrictions': product.restrictions,
    }


def build_brand_dna_brief_content(brand: Brand) -> str:
    return json.dumps(build_brand_dna_request(brand))


def build_product_dna_brief_content(product: Product) -> str:
    return json.dumps(build_product_dna_request(product))


def build_brand_dna_job_title(brand: Brand) -> str:
    return f'{BRAND_DNA_JOB_PREFIX}{brand.name}'


def build_product_dna_job_title(product: Product) -> str:
    return f'{PRODUCT_DNA_JOB_PREFIX}{product.name}'


def build_brand_dna_brief_title(brand: Brand) -> str:
    return f'{BRAND_DNA_BRIEF_PREFIX}{brand.name}'


def build_product_dna_brief_title(product: Product) -> str:
    return f'{PRODUCT_DNA_BRIEF_PREFIX}{product.name}'


def parse_dna_generation_request(brief: Brief | None) -> dict[str, Any] | None:
    if brief is None or not brief.content:
        return None
    try:
        payload = json.loads(brief.content)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if payload.get('kind') not in {BRAND_DNA_BRIEF_KIND, PRODUCT_DNA_BRIEF_KIND}:
        return None
    return payload


def parse_dna_generation_output(output_text: str | None) -> dict[str, Any] | None:
    if output_text is None:
        return None
    text = output_text.strip()
    if not text:
        return None
    if text.startswith('```'):
        text = text.strip('`')
        if text.startswith('json\n'):
            text = text[5:]
    if text.startswith('<json>') and text.endswith('</json>'):
        text = text[len('<json>') : -len('</json>')].strip()
    candidates = [text]
    start = text.find('{')
    end = text.rfind('}')
    if 0 <= start < end:
        candidates.append(text[start : end + 1])
    for candidate in candidates:
        try:
            payload = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return None


def parse_uuid(value: Any) -> UUID | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return UUID(value)
    except ValueError:
        return None
