#!/bin/sh
# Auto-apply DB migrations before starting the API so the live schema never
# lags behind the code. Idempotent: alembic upgrade head is a no-op when the
# DB is already current.
set -e
cd /app
echo "[entrypoint] Applying database migrations (alembic upgrade head)..."
alembic upgrade head
echo "[entrypoint] Migrations up to date. Starting: $*"
exec "$@"
