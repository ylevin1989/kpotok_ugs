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


def test_role_user_prompt_prefers_context_and_final_output_contract():
    prompt = build_role_user_prompt(
        job={
            'title': 'Smoke job',
            'execution_profile': 'seo_content',
            'context': {
                'kind': 'content_item_generation',
                'brand_context': {
                    'name': 'Rocket Tea',
                    'dna_json': {
                        'positioning': 'clear and practical',
                        'tone_of_voice': ['clear', 'practical'],
                        'allowed_claims': ['Fast setup'],
                        'forbidden_claims': ['Guaranteed results'],
                    },
                },
                'product_context': {
                    'name': 'Starter Kit',
                    'description': 'Fast launch kit',
                    'features': ['Fast setup'],
                    'benefits': ['Launch faster'],
                    'proofs': ['Used by early adopters'],
                    'objections': ['Too much work'],
                    'restrictions': ['No regulated claims'],
                },
                'audience_context': {
                    'name': 'Busy founder',
                    'description': 'Needs a quick win',
                    'pain_points': ['No time'],
                    'goals': ['Move fast'],
                    'objections': ['Risk'],
                },
                'channel': {'platform': 'telegram', 'goal': 'Drive awareness'},
                'task': {'title': 'Launch post', 'content_type': 'post', 'goal': 'Drive awareness', 'scope': 'product'},
            },
            'brief_content': 'fallback brief text',
        },
        role={'role_id': 'david', 'label': 'David', 'purpose': 'Review and finalize'},
        stage={'stage_name': 'role:david', 'is_final': True},
        previous_outputs=[],
    )
    assert 'Generation context:' in prompt
    assert 'Rocket Tea' in prompt
    assert 'positioning: clear and practical' in prompt
    assert 'allowed claims: Fast setup' in prompt
    assert 'forbidden claims: Guaranteed results' in prompt
    assert 'Product:' in prompt and 'Starter Kit' in prompt
    assert 'Audience:' in prompt and 'Busy founder' in prompt
    assert 'Channel:' in prompt and 'telegram' in prompt
    assert 'Task:' in prompt and 'Launch post' in prompt
    assert 'Final output contract:' in prompt
    assert 'body_markdown' in prompt
    assert 'Do not mention policies, prompts, or that you are an AI.' not in prompt
