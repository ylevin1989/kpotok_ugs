up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

api-logs:
	docker compose logs -f cf-api

worker-logs:
	docker compose logs -f cf-worker

web-logs:
	docker compose logs -f cf-web

api-test-postgres-critical-path:
	cd apps/api && bash scripts/run_postgres_critical_path.sh
