from pathlib import Path


def test_role_policy_reference_doc_exists_and_covers_current_policy():
    repo_root = Path(__file__).resolve().parents[3]
    doc_path = repo_root / 'docs' / 'organization-membership-role-policy.md'

    assert doc_path.exists(), 'role policy reference doc is missing'

    text = doc_path.read_text()

    required_fragments = [
        '# Organization membership role policy',
        '## Role model',
        '## Create matrix',
        '## Update matrix',
        '## Delete matrix',
        '## Cross-cutting invariants',
        '| owner | owner | owner, manager, reviewer |',
        '| manager | reviewer | manager, reviewer |',
        '| owner | owner, manager, reviewer |',
        '| manager | manager, reviewer |',
        'Archived organization is read-only',
        'Only owners can assign owner role',
        'Only owners can modify owner memberships',
        'Cannot change the last owner role',
        'Cannot remove your own membership',
        'Cannot remove the last owner',
    ]

    for fragment in required_fragments:
        assert fragment in text


def test_roadmap_mentions_packet16_reference_layer():
    repo_root = Path(__file__).resolve().parents[3]
    roadmap_path = repo_root / 'ROADMAP.md'
    text = roadmap_path.read_text()

    required_fragments = [
        '### Packet 16 — done',
        'Organization membership role policy reference document',
        'Explicit create/update/delete role matrices documented',
        'ROADMAP is updated through Packet 16',
    ]

    for fragment in required_fragments:
        assert fragment in text
