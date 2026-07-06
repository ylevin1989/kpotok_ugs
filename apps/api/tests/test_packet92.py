from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_dashboard_role_gating_contract_for_mvp07():
    dashboard_text = (REPO_ROOT / 'apps/web/app/dashboard/page.tsx').read_text()

    assert "const canManageSelectedOrganization" in dashboard_text
    assert "client_owner" in dashboard_text
    assert "client_manager" in dashboard_text
    assert "Этот scope для reviewer работает в режиме только чтения." in dashboard_text
    assert "Создавать briefs и jobs здесь могут только manager/owner." in dashboard_text
    assert "У reviewer нет права создавать brief в этом scope." in dashboard_text
    assert "У reviewer нет права ставить job в очередь в этом scope." in dashboard_text
