from pathlib import Path

from app.testing.db_env import build_test_database_config


def test_build_test_database_config_uses_postgres_url_when_requested(monkeypatch):
    monkeypatch.setenv('TEST_DB_BACKEND', 'postgres')
    monkeypatch.setenv('TEST_DATABASE_URL', 'postgresql+psycopg://postgres:postgres@127.0.0.1:55432/content_factory_test')

    config = build_test_database_config()

    assert config.backend == 'postgres'
    assert config.database_url == 'postgresql+psycopg://postgres:postgres@127.0.0.1:55432/content_factory_test'
    assert config.cleanup_path is None


def test_build_test_database_config_uses_temp_sqlite_by_default(monkeypatch):
    monkeypatch.delenv('TEST_DB_BACKEND', raising=False)
    monkeypatch.delenv('TEST_DATABASE_URL', raising=False)

    config = build_test_database_config()

    assert config.backend == 'sqlite'
    assert config.database_url.startswith('sqlite:///')
    assert isinstance(config.cleanup_path, Path)
