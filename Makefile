.PHONY: test-backend test-frontend test-e2e test-all coverage

test-backend:
	@echo "Running Backend Tests..."
	@docker run --rm -v "$$(pwd)/backend:/app" --network lucky-panda_default \
		-e POSTGRES_SERVER=db \
		-e MINIO_ENDPOINT=minio:9000 \
		lucky-panda-backend sh -c "pip install pytest pytest-asyncio pytest-cov && PYTHONPATH=. python -m pytest tests"

test-frontend:
	@echo "Running Frontend Unit Tests..."
	@cd frontend && npm test

test-e2e:
	@echo "Running End-to-End Tests..."
	@cd frontend && npx playwright test

test-all: test-backend test-frontend test-e2e
	@echo "All tests passed with high rigor!"

coverage:
	@echo "Generating Coverage Report..."
	@PYTHONPATH=backend backend/venv/bin/pytest --cov=backend/app backend/tests --cov-report=html
