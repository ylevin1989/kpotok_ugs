from dataclasses import dataclass
from pathlib import Path
import tempfile


@dataclass(frozen=True)
class TestDatabaseConfig:
    backend: str
    database_url: str
    cleanup_path: Path | None = None


def build_test_database_config() -> TestDatabaseConfig:
    import os

    backend = os.environ.get('TEST_DB_BACKEND', 'sqlite').strip().lower()
    if backend == 'postgres':
        database_url = os.environ['TEST_DATABASE_URL']
        return TestDatabaseConfig(backend='postgres', database_url=database_url, cleanup_path=None)

    cleanup_path = Path(tempfile.gettempdir()) / 'content_factory_test.db'
    return TestDatabaseConfig(
        backend='sqlite',
        database_url=f'sqlite:///{cleanup_path}',
        cleanup_path=cleanup_path,
    )
