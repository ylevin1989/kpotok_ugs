from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cf_api_runtime_is_production_hardened():
    compose_text = (REPO_ROOT / 'docker-compose.yml').read_text()
    dockerfile_text = (REPO_ROOT / 'infra/docker/api.Dockerfile').read_text()

    assert 'command: uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload' not in compose_text
    assert 'command: uvicorn app.main:app --host 0.0.0.0 --port 8100' in compose_text
    assert '--reload' not in dockerfile_text
    assert 'CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8100"]' in dockerfile_text
