import atexit
import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.testing.db_env import build_test_database_config

TEST_DB_CONFIG = build_test_database_config()
if TEST_DB_CONFIG.cleanup_path and TEST_DB_CONFIG.cleanup_path.exists():
    TEST_DB_CONFIG.cleanup_path.unlink()
if TEST_DB_CONFIG.cleanup_path:
    atexit.register(lambda: TEST_DB_CONFIG.cleanup_path.exists() and TEST_DB_CONFIG.cleanup_path.unlink())
os.environ['DATABASE_URL'] = TEST_DB_CONFIG.database_url
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['HERMES_BASE_URL'] = 'https://ha.uno-ai.pw'
os.environ['JWT_SECRET'] = 'test-secret'
os.environ['WORKER_TOKEN'] = 'packet23-worker-token'

from app.core.config import get_settings
get_settings.cache_clear()
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.main import app


@pytest.fixture(autouse=True)
def reset_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    SessionLocal.remove() if hasattr(SessionLocal, 'remove') else None


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client
