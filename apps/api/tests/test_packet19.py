from pydantic import ValidationError

from app.core.config import Settings


def test_settings_require_database_url(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('database_url', raising=False)

    try:
        Settings(_env_file=None)
        raised = None
    except ValidationError as exc:
        raised = exc

    assert raised is not None
    assert 'database_url' in str(raised)


def test_settings_reject_default_jwt_secret_outside_test_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@localhost:5432/content_factory')
    monkeypatch.setenv('ENV', 'production')
    monkeypatch.setenv('JWT_SECRET', 'change_me')

    try:
        Settings(_env_file=None)
        raised = None
    except ValidationError as exc:
        raised = exc

    assert raised is not None
    assert 'jwt_secret' in str(raised)
