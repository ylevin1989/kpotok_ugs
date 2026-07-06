from enum import Enum


class ContentScope(str, Enum):
    BRAND = 'brand'
    PRODUCT = 'product'
    CAMPAIGN = 'campaign'
    COMPARISON = 'comparison'


PRODUCT_SCOPES = {ContentScope.PRODUCT}


def requires_product_id(scope: ContentScope) -> bool:
    return scope in PRODUCT_SCOPES
