.PHONY: dev full down logs ps check test lint format typecheck security migrate shell profiles scaled-workers default-worker monitoring mail storage db-tools edge scheduled validate

dev:
	docker compose up -d --build

full:
	docker compose --profile edge --profile scheduled --profile storage --profile mail --profile db-tools --profile monitoring up -d --build

down:
	docker compose down

logs:
	docker compose logs -f web worker

ps:
	docker compose ps

check:
	docker compose exec web python manage.py check

test:
	docker compose exec web pytest

lint:
	docker compose exec web ruff check .

format:
	docker compose exec web ruff format .

typecheck:
	docker compose exec web mypy cctv_analytics platform_core incidents

security:
	docker compose exec web bandit -r cctv_analytics platform_core incidents -x incidents/migrations

migrate:
	docker compose exec web python manage.py migrate

shell:
	docker compose exec web python manage.py shell_plus

profiles:
	docker compose config --profiles

scaled-workers:
	docker compose stop worker
	docker compose --profile workers up -d worker-imports worker-analytics

default-worker:
	docker compose --profile workers stop worker-imports worker-analytics
	docker compose up -d worker

monitoring:
	docker compose --profile monitoring up -d flower prometheus grafana

mail:
	docker compose --profile mail up -d mailpit

storage:
	docker compose --profile storage up -d minio minio-init

db-tools:
	docker compose --profile db-tools up -d adminer

edge:
	docker compose --profile edge up -d nginx

scheduled:
	docker compose --profile scheduled up -d beat

validate:
	python scripts/validate_project.py
