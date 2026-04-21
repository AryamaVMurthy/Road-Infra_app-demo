.PHONY: dev-up dev-down dev-logs dev-ps test-backend test-gateway test-frontend test-e2e test-all

dev-up:
	@./scripts/dev_up.sh

dev-down:
	@docker compose down

dev-logs:
	@docker compose logs -f --tail=200 frontend backend vlm-gateway llama-server

dev-ps:
	@docker compose ps

test-backend:
	@PYTHONPATH=backend .venv/bin/pytest backend/tests -q

test-gateway:
	@PYTHONPATH=$$(pwd) .venv/bin/pytest vlm_gateway/tests -q

test-frontend:
	@npm --prefix frontend run lint
	@npm --prefix frontend run test
	@npm --prefix frontend run build

test-e2e:
	@npm --prefix frontend exec playwright test

test-all: test-backend test-gateway test-frontend test-e2e
