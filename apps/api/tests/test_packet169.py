from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def read_text(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding='utf-8')


def test_internal_execution_bundle_documents_core_contract():
    bundle = read_text('docs/internal-execution-api-bundle.md')

    assert '# Internal execution API bundle' in bundle
    assert '`execution_profile`' in bundle
    assert '`internal_role_plan`' in bundle
    assert 'general_content' in bundle
    assert 'seo_content' in bundle
    assert 'docs/internal-roles.md' in bundle
    assert 'docs/jobs-api-reference.md' in bundle


def test_readme_links_internal_execution_bundle():
    readme = read_text('README.md')

    assert '## Internal execution API bundle' in readme
    assert 'docs/internal-execution-api-bundle.md' in readme
    assert 'execution_profile' in readme
    assert 'internal_role_plan' in readme


def test_roadmap_marks_internal_execution_bundle_packet_done():
    roadmap = read_text('ROADMAP.md')

    assert '### Internal Execution API Bundle Packet 01 — done' in roadmap
    assert 'public API reference / developer docs bundle' in roadmap
    assert 'docs/internal-execution-api-bundle.md' in roadmap
