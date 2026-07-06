from __future__ import annotations

from dataclasses import dataclass
import json
import re
from collections.abc import Iterable

from app.db.models.brand import Brand
from app.db.models.content_item import ContentItem
from app.db.models.content_version import ContentVersion
from app.db.models.product import Product
from app.db.models.ticket import Ticket


_RISK_PATTERNS: tuple[tuple[str, str], ...] = (
    (r'\bguaranteed\b', 'Guarantee language can overstate certainty.'),
    (r'\b100%\b', 'Percent-certainty language can overstate certainty.'),
    (r'\bmiracle\b', 'Miracle language is high-risk marketing language.'),
    (r'\bcure\b', 'Medical-style claim language is high-risk.'),
    (r'\binstant results?\b', 'Instant-results language is high-risk.'),
    (r'\bno risk\b', 'No-risk language is a risky absolute claim.'),
    (r'\bbest ever\b', 'Superlative language is over-promising.'),
)


@dataclass(slots=True)
class QualityCheckEvaluation:
    score: int
    threshold: int
    status: str
    summary: str
    checks_json: dict
    issues_json: list[str]
    recommendations_json: list[str]
    content_status: str


def _flatten_text_fragments(value: object) -> Iterable[str]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, dict):
        pieces: list[str] = []
        for key, item in value.items():
            pieces.extend(_flatten_text_fragments(key))
            pieces.extend(_flatten_text_fragments(item))
        return pieces
    if isinstance(value, Iterable):
        pieces: list[str] = []
        for item in value:
            pieces.extend(_flatten_text_fragments(item))
        return pieces
    return (str(value),)


def _normalize_phrase(value: str) -> str:
    return re.sub(r'\s+', ' ', value.strip().lower())


def _collect_terms(*values: object) -> list[str]:
    terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        for fragment in _flatten_text_fragments(value):
            fragment = _normalize_phrase(fragment)
            if len(fragment) < 3:
                continue
            if fragment not in seen:
                seen.add(fragment)
                terms.append(fragment)
    return terms


def _contains_phrase(text: str, phrase: str) -> bool:
    if not phrase:
        return False
    if len(phrase.split()) == 1:
        return re.search(rf'\b{re.escape(phrase)}\b', text) is not None
    return phrase in text


def _matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if _contains_phrase(text, term)]


def _normalized_content_text(content_version: ContentVersion) -> str:
    pieces: list[str] = []
    if content_version.body_markdown:
        pieces.append(content_version.body_markdown)
    if content_version.structured_json is not None:
        pieces.append(json.dumps(content_version.structured_json, sort_keys=True, default=str))
    return _normalize_phrase(' '.join(pieces))


def evaluate_quality_check(
    *,
    content_item: ContentItem,
    content_version: ContentVersion,
    brand: Brand,
    product: Product | None,
    ticket: Ticket | None = None,
    threshold: int = 80,
) -> QualityCheckEvaluation:
    text = _normalized_content_text(content_version)

    brand_terms = _collect_terms(
        brand.name,
        brand.slug,
        brand.dna_json,
    )
    product_terms = _collect_terms(
        product.name if product is not None else None,
        product.category if product is not None else None,
        product.description if product is not None else None,
        product.features if product is not None else None,
        product.benefits if product is not None else None,
        product.proofs if product is not None else None,
        product.objections if product is not None else None,
        product.restrictions if product is not None else None,
        product.dna_json if product is not None else None,
    )
    audience_terms = _collect_terms(
        content_item.platform,
        content_item.content_type,
        content_item.goal,
        content_item.title,
        ticket.type if ticket is not None else None,
        ticket.reason_codes if ticket is not None else None,
        ticket.comment if ticket is not None else None,
    )

    matched_brand_terms = _matched_terms(text, brand_terms)
    matched_product_terms = _matched_terms(text, product_terms)
    matched_audience_terms = _matched_terms(text, audience_terms)

    brand_match_score = min(100, 60 + len(matched_brand_terms) * 10)
    product_accuracy_score = min(100, 55 + len(matched_product_terms) * 12)
    audience_match_score = min(100, 65 + len(matched_audience_terms) * 8)

    risk_flags = [label for pattern, label in _RISK_PATTERNS if re.search(pattern, text)]
    if text.count('!') >= 3:
        risk_flags.append('Overuse of exclamation marks makes the draft feel shouty.')
    if len(text) < 120:
        risk_flags.append('Content is too short to carry enough proof and context.')
    if ticket is not None and ticket.reason_codes:
        for reason in ticket.reason_codes:
            if reason in {'off_brand', 'too_salesy', 'wrong_tone'}:
                risk_flags.append(f'Ticket reason {reason} suggests an elevated editorial risk.')
                break

    risk_score = min(100, 10 + len(risk_flags) * 20)
    quality_score = round(
        0.35 * brand_match_score
        + 0.4 * product_accuracy_score
        + 0.15 * audience_match_score
        + 0.1 * (100 - risk_score)
    )

    passes_gate = quality_score >= threshold and product_accuracy_score >= 90 and risk_score <= 30
    content_status = 'waiting_client_review' if passes_gate else 'internal_review'
    status = 'passed' if passes_gate else ('failed' if risk_score > 60 else 'needs_revision')

    missing_brand_terms = [term for term in brand_terms if term not in matched_brand_terms][:4]
    missing_product_terms = [term for term in product_terms if term not in matched_product_terms][:4]
    missing_audience_terms = [term for term in audience_terms if term not in matched_audience_terms][:4]

    issues_json: list[str] = []
    if missing_brand_terms:
        issues_json.append(f'Missing brand signals: {", ".join(missing_brand_terms)}')
    if missing_product_terms:
        issues_json.append(f'Missing product signals: {", ".join(missing_product_terms)}')
    if missing_audience_terms:
        issues_json.append(f'Missing audience/context signals: {", ".join(missing_audience_terms)}')
    issues_json.extend(risk_flags)

    recommendations_json: list[str] = []
    if passes_gate:
        recommendations_json.append('Publish to client review.')
    else:
        if product_accuracy_score < 90:
            recommendations_json.append('Strengthen product-specific facts, benefits, or proof points.')
        if brand_match_score < 80:
            recommendations_json.append('Bring the brand voice and positioning closer to the brand DNA.')
        if risk_score > 30:
            recommendations_json.append('Remove risky or over-promising language.')
        if audience_match_score < 75:
            recommendations_json.append('Tighten the audience hook and platform-specific angle.')

    summary = (
        f'Quality check {status}: score {quality_score}, '
        f'brand match {brand_match_score}, product accuracy {product_accuracy_score}, risk {risk_score}.'
    )

    checks_json = {
        'brand_match_score': brand_match_score,
        'product_accuracy_score': product_accuracy_score,
        'audience_match_score': audience_match_score,
        'risk_score': risk_score,
        'thresholds': {
            'quality_score': threshold,
            'product_accuracy_score': 90,
            'risk_score_max': 30,
        },
        'matched_brand_terms': matched_brand_terms,
        'matched_product_terms': matched_product_terms,
        'matched_audience_terms': matched_audience_terms,
        'risk_flags': risk_flags,
    }
    if ticket is not None:
        checks_json['ticket_id'] = str(ticket.id)
        checks_json['ticket_reason_codes'] = list(ticket.reason_codes or [])
    return QualityCheckEvaluation(
        score=quality_score,
        threshold=threshold,
        status=status,
        summary=summary,
        checks_json=checks_json,
        issues_json=issues_json,
        recommendations_json=recommendations_json,
        content_status=content_status,
    )
