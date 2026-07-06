#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="${TEST_POSTGRES_CONTAINER_NAME:-cf-test-postgres-lane}"
HOST_PORT="${TEST_POSTGRES_PORT:-55432}"
DB_NAME="${TEST_POSTGRES_DB:-content_factory_test}"
DB_USER="${TEST_POSTGRES_USER:-postgres}"
DB_PASSWORD="${TEST_POSTGRES_PASSWORD:-postgres}"
POSTGRES_IMAGE="${TEST_POSTGRES_IMAGE:-postgres:16}"
API_TEST_IMAGE="${API_TEST_IMAGE:-content-factory-cf-api}"
DATABASE_URL="postgresql+psycopg://${DB_USER}:${DB_PASSWORD}@127.0.0.1:${HOST_PORT}/${DB_NAME}"
TEST_TARGETS=(
  tests/test_packet03.py
  tests/test_packet07.py
  tests/test_packet15.py
  tests/test_packet17.py
  tests/test_packet18.py
)

cleanup() {
  docker rm -f "${CONTAINER_NAME}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

if ! command -v docker >/dev/null 2>&1; then
  echo "docker is required for the Postgres critical-path lane" >&2
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "docker daemon is not reachable; run this lane on a host with Docker access" >&2
  exit 1
fi

if ! docker image inspect "${API_TEST_IMAGE}" >/dev/null 2>&1; then
  cat >&2 <<EOF
API test image '${API_TEST_IMAGE}' was not found.
Build it first, for example:
  docker compose build cf-api
or set API_TEST_IMAGE to an existing compatible image.
EOF
  exit 1
fi

cleanup

docker run -d \
  --name "${CONTAINER_NAME}" \
  -e POSTGRES_DB="${DB_NAME}" \
  -e POSTGRES_USER="${DB_USER}" \
  -e POSTGRES_PASSWORD="${DB_PASSWORD}" \
  -p "127.0.0.1:${HOST_PORT}:5432" \
  "${POSTGRES_IMAGE}" >/dev/null

for _ in $(seq 1 30); do
  if docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "${CONTAINER_NAME}" pg_isready -U "${DB_USER}" -d "${DB_NAME}" >/dev/null

TEST_TARGETS_ARGS="$(printf '%q ' "${TEST_TARGETS[@]}")"

docker run --rm \
  --network host \
  -v "$(pwd):/app" \
  -w /app \
  "${API_TEST_IMAGE}" \
  sh -lc "uv pip install --system -e '.[dev]' >/tmp/pg-lane-install.log 2>&1 && TEST_DB_BACKEND=postgres TEST_DATABASE_URL='${DATABASE_URL}' pytest ${TEST_TARGETS_ARGS} -q"
