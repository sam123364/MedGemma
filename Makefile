.PHONY: bootstrap dev backend frontend test migrate

bootstrap:
	./scripts/bootstrap.sh

dev:
	./scripts/dev.sh

backend:
	. .venv/bin/activate && cd backend && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev -- --port 3000

test:
	. .venv/bin/activate && cd backend && pytest

migrate:
	. .venv/bin/activate && cd backend && alembic upgrade head
