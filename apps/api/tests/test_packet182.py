from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dashboard_exposes_execution_profile_reference_for_operators():
    dashboard_text = (REPO_ROOT / 'apps/web/app/dashboard/page.tsx').read_text()

    assert 'const EXECUTION_PROFILE_REFERENCE = [' in dashboard_text
    assert "key: 'general_content'" in dashboard_text
    assert "key: 'seo_content'" in dashboard_text
    assert "key: 'ads_content'" in dashboard_text
    assert "key: 'architecture_support'" in dashboard_text
    assert '<h3>Execution profile reference</h3>' in dashboard_text
    assert 'docs/internal-execution-api-bundle.md' in dashboard_text
    assert "profile.roles.join(' → ')" in dashboard_text


def test_internal_execution_bundle_remains_the_source_of_truth_for_contract_discovery():
    bundle_text = (REPO_ROOT / 'docs/internal-execution-api-bundle.md').read_text()

    assert '# Internal execution API bundle' in bundle_text
    assert 'execution_profile' in bundle_text
    assert 'internal_role_plan' in bundle_text
    assert 'general_content' in bundle_text
    assert 'architecture_support' in bundle_text
