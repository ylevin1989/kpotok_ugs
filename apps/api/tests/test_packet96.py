from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_types_expose_internal_execution_fields_for_jobs():
    types_text = (REPO_ROOT / 'apps/web/lib/types.ts').read_text()

    assert 'export interface InternalRolePlanItemRead' in types_text
    assert 'execution_profile: string;' in types_text
    assert 'internal_role_plan: InternalRolePlanItemRead[];' in types_text


def test_dashboard_job_detail_renders_internal_execution_plan_contract():
    dashboard_text = (REPO_ROOT / 'apps/web/app/dashboard/page.tsx').read_text()

    assert 'function formatExecutionProfile' in dashboard_text
    assert '<h3>Internal execution plan</h3>' in dashboard_text
    assert 'Execution profile' in dashboard_text
    assert 'selectedJob.execution_profile' in dashboard_text
    assert 'selectedJob.internal_role_plan.length' in dashboard_text
    assert 'selectedJob.internal_role_plan.map((role, index) => (' in dashboard_text
    assert 'role.role_id' in dashboard_text
    assert 'role.label' in dashboard_text
    assert 'role.purpose' in dashboard_text
    assert 'У этой job пока нет internal role plan.' in dashboard_text
