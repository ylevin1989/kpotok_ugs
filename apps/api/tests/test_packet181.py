from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_web_types_expose_compact_trace_summary_for_jobs():
    types_text = (REPO_ROOT / 'apps/web/lib/types.ts').read_text()

    assert 'export interface JobExecutionTraceCompactSummaryRead' in types_text
    assert 'trace_compact_summary?: JobExecutionTraceCompactSummaryRead | null;' in types_text
    assert 'latest_worker_metadata_keys?: string[] | null;' in types_text


def test_dashboard_job_detail_renders_compact_trace_summary_contract():
    dashboard_text = (REPO_ROOT / 'apps/web/app/dashboard/page.tsx').read_text()

    assert '<h3>Compact trace summary</h3>' in dashboard_text
    assert 'execution_trace.trace_compact_summary' in dashboard_text
    assert 'selectedJob.execution_trace?.trace_compact_summary' in dashboard_text
    assert 'Current stage' in dashboard_text
    assert 'Latest worker metadata keys' in dashboard_text
    assert 'У этой job ещё нет compact trace summary.' in dashboard_text
