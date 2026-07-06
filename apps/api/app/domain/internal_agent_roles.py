from typing import TypedDict


class InternalRoleDef(TypedDict):
    role_id: str
    label: str
    purpose: str


ROLE_REGISTRY: dict[str, InternalRoleDef] = {
    'mike': {
        'role_id': 'mike',
        'label': 'Mike',
        'purpose': 'Internal production manager who routes tasks and frames execution order.',
    },
    'emma': {
        'role_id': 'emma',
        'label': 'Emma',
        'purpose': 'Product manager who protects product meaning and desired outcome.',
    },
    'iris': {
        'role_id': 'iris',
        'label': 'Iris',
        'purpose': 'Researcher who derives market, ICP, pains, and trend inputs.',
    },
    'sarah': {
        'role_id': 'sarah',
        'label': 'Sarah',
        'purpose': 'SEO specialist who shapes organic search angles and keyword intent.',
    },
    'adrian': {
        'role_id': 'adrian',
        'label': 'Adrian',
        'purpose': 'Ads specialist who shapes offers, hooks, and paid acquisition angles.',
    },
    'alex': {
        'role_id': 'alex',
        'label': 'Alex',
        'purpose': 'Content constructor who assembles drafts, scripts, and visual/content briefs.',
    },
    'david': {
        'role_id': 'david',
        'label': 'David',
        'purpose': 'Data analyst who reviews consistency, deviations, and efficiency signals.',
    },
    'bob': {
        'role_id': 'bob',
        'label': 'Bob',
        'purpose': 'Architect who handles process/system issues and integration thinking.',
    },
}

DEFAULT_EXECUTION_PROFILE = 'general_content'

EXECUTION_PROFILES: dict[str, list[str]] = {
    'general_content': ['mike', 'emma', 'iris', 'alex', 'david'],
    'seo_content': ['mike', 'emma', 'iris', 'sarah', 'alex', 'david'],
    'ads_content': ['mike', 'emma', 'iris', 'adrian', 'alex', 'david'],
    'architecture_support': ['mike', 'bob', 'david'],
}


def get_execution_profile(name: str | None) -> str:
    profile = name or DEFAULT_EXECUTION_PROFILE
    if profile not in EXECUTION_PROFILES:
        raise ValueError(f'Unknown execution profile: {profile}')
    return profile


def resolve_internal_role_plan(name: str | None) -> tuple[str, list[InternalRoleDef]]:
    profile = get_execution_profile(name)
    role_ids = EXECUTION_PROFILES[profile]
    return profile, [ROLE_REGISTRY[role_id] for role_id in role_ids]
