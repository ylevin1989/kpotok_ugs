import pytest
from pydantic import ValidationError

from app.domain.content_scope import ContentScope, requires_product_id
from app.schemas.scope import GenerationScope


def test_requires_product_id_only_for_product_scope():
    assert requires_product_id(ContentScope.PRODUCT) is True
    assert requires_product_id(ContentScope.BRAND) is False
    assert requires_product_id(ContentScope.CAMPAIGN) is False
    assert requires_product_id(ContentScope.COMPARISON) is False


def test_generation_scope_requires_product_id_for_product_scope():
    ok = GenerationScope(scope=ContentScope.BRAND)
    assert ok.scope == ContentScope.BRAND
    assert ok.product_id is None

    with pytest.raises(ValidationError):
        GenerationScope(scope=ContentScope.PRODUCT)
