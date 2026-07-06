from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dashboard_job_form_exposes_execution_profile_selector():
    dashboard_text = (REPO_ROOT / 'apps/web/app/dashboard/page.tsx').read_text()

    assert "const [selectedExecutionProfile, setSelectedExecutionProfile] = useState('general_content');" in dashboard_text
    assert '<span>Execution profile</span>' in dashboard_text
    assert 'setSelectedExecutionProfile(event.target.value)' in dashboard_text
    assert 'EXECUTION_PROFILE_REFERENCE.map((profile) => (' in dashboard_text
    assert 'execution_profile: selectedExecutionProfile' in dashboard_text


def test_web_api_client_allows_optional_execution_profile_on_job_creation():
    api_text = (REPO_ROOT / 'apps/web/lib/api.ts').read_text()

    assert 'execution_profile?: string' in api_text
    assert "payload: { organization_id: string; brand_id: string; brief_id: string; title: string; execution_profile?: string }" in api_text
