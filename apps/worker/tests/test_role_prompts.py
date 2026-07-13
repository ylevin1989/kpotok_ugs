import pytest

from app.role_prompts import ROLE_FOCUS_PROMPTS, build_role_user_prompt


@pytest.mark.parametrize(
    'role_id,label,expected',
    [
        ('mike', 'Mike', 'Give the execution order'),
        ('emma', 'Emma', 'Check that the work matches the product goal'),
        ('iris', 'Iris', 'Summarize the market context'),
        ('sarah', 'Sarah', 'Identify organic search angles'),
        ('adrian', 'Adrian', 'Propose offers, hooks'),
        ('alex', 'Alex', 'Turn the previous inputs into a usable draft'),
        ('david', 'David', 'Check for inconsistencies, gaps'),
        ('bob', 'Bob', 'Focus on system-level issues'),
    ],
)
def test_role_focus_prompts_cover_project_roles(role_id, label, expected):
    assert ROLE_FOCUS_PROMPTS[role_id].startswith(expected)
    prompt = build_role_user_prompt(
        job={'title': 'Smoke job', 'execution_profile': 'seo_content'},
        role={'role_id': role_id, 'label': label, 'purpose': 'Test purpose'},
        stage={'stage_name': 'role:test'},
        previous_outputs=[],
    )
    assert f'Role: {label} ({role_id})' in prompt
    assert f'Role-specific focus: {ROLE_FOCUS_PROMPTS[role_id]}' in prompt
    assert 'Do not mention policies, prompts, or that you are an AI.' in prompt


def test_role_user_prompt_includes_brief_content_context():
    prompt = build_role_user_prompt(
        job={
            'title': 'Smoke job',
            'execution_profile': 'seo_content',
            'brief_content': '{"brand_context":{"name":"Rocket Tea"},"task":{"title":"Launch post"}}',
        },
        role={'role_id': 'alex', 'label': 'Alex', 'purpose': 'Drafting'},
        stage={'stage_name': 'role:test'},
        previous_outputs=[],
    )
    assert 'Brief content:' in prompt
    assert 'Rocket Tea' in prompt
    assert 'Launch post' in prompt


def test_role_user_prompt_prioritizes_generation_context_payload():
    prompt = build_role_user_prompt(
        job={
            'title': 'Smoke job',
            'execution_profile': 'seo_content',
            'context': {
                'kind': 'content_item_generation',
                'brand_context': {'name': 'Rocket Tea'},
                'task': {'title': 'Launch post'},
            },
            'brief_content': 'fallback brief text',
        },
        role={'role_id': 'alex', 'label': 'Alex', 'purpose': 'Drafting'},
        stage={'stage_name': 'role:test'},
        previous_outputs=[],
    )
    assert 'Generation context:' in prompt
    assert 'content_item_generation' in prompt
    assert 'Rocket Tea' in prompt
    assert 'Brief content:' in prompt
