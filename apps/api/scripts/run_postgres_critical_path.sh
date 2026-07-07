#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${TEST_POSTGRES_CONTAINER_NAME:-cf-postgres}"
HOST_PORT="${TEST_POSTGRES_PORT:-5432}"
DB_NAME="${TEST_POSTGRES_DB:-content_factory_test}"
DB_USER="${TEST_POSTGRES_USER:-$(docker exec cf-postgres printenv POSTGRES_USER)}"
DB_PASSWORD="${TEST_POSTGRES_PASSWORD:-$(docker exec cf-postgres printenv POSTGRES_PASSWORD)}"
REPO_ROOT="${TEST_POSTGRES_REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)}"
DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${HOST_PORT}/${DB_NAME}"
TEST_TARGETS=(
  tests/test_packet03.py
  tests/test_packet07.py
  tests/test_packet15.py
  tests/test_packet17.py
  tests/test_packet18.py
  tests/test_packet199.py
  tests/test_packet200.py
  tests/test_packet201.py
  tests/test_packet202.py
  tests/test_packet203.py
  tests/test_packet204.py
  tests/test_packet205.py
)

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the Postgres critical-path lane" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "docker daemon is not reachable; run this lane on a host with Docker access" >&2
  exit 1
fi

if ! docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1; then
  cat >&2 <<EOF
Postgres container '${CONTAINER_NAME}' was not found.
Start the shared database container first, or override TEST_POSTGRES_CONTAINER_NAME.
EOF
  exit 1
fi

ready=0
for _ in $(seq 1 60); do
  if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    ready=1
    break
  fi
  sleep 1
done

if [ "${ready}" -ne 1 ]; then
  echo "Postgres lane database did not become ready in time" >&2
  exit 1
fi

if ! docker exec "${CONTAINER_NAME}" psql -U "${DB_USER}" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1; then
  docker exec "${CONTAINER_NAME}" createdb -U "${DB_USER}" "${DB_NAME}"
fi

cd "${REPO_ROOT}/apps/api"
TEST_DB_BACKEND=postgres TEST_DATABASE_URL="${DATABASE_URL}" uv run pytest -q "${TEST_TARGETS[@]}"
