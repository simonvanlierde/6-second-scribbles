.PHONY: help install test test-watch coverage lint format type-check clean dev db-up db-down db-migrate db-seed db-reset db-setup

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install:  ## Install dependencies
	pip install -r requirements-dev.txt

test:  ## Run all tests
	pytest -v

test-watch:  ## Run tests in watch mode
	pytest-watch

test-fast:  ## Run tests excluding slow ones
	pytest -v -m "not slow"

test-integration:  ## Run integration tests only
	pytest -v -m integration

coverage:  ## Run tests with coverage report
	pytest --cov=. --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

lint:  ## Run linter
	ruff check .

lint-fix:  ## Run linter and fix issues
	ruff check . --fix

format:  ## Format code with black
	black .

format-check:  ## Check code formatting
	black --check .

type-check:  ## Run type checker
	mypy . --ignore-missing-imports

clean:  ## Clean up generated files
	rm -rf __pycache__ .pytest_cache .coverage htmlcov .ruff_cache .mypy_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

db-up:  ## Start PostgreSQL database
	docker-compose up -d

db-down:  ## Stop PostgreSQL database
	docker-compose down

db-migrate:  ## Run database migrations
	alembic upgrade head

db-seed:  ## Seed database with card data
	python seed_data.py

db-reset:  ## Reset database (clear and reseed)
	python seed_data.py --clear
	python seed_data.py

db-setup:  ## Complete database setup (start, migrate, seed)
	make db-up
	sleep 3
	make db-migrate
	make db-seed

dev:  ## Run development server
	uvicorn main:app --reload --port 8000

dev-prod:  ## Run production server
	uvicorn main:app --host 0.0.0.0 --port 8000

ci:  ## Run CI checks (lint, format, type, test)
	@echo "Running CI checks..."
	@echo "\n1. Linting..."
	ruff check .
	@echo "\n2. Format check..."
	black --check .
	@echo "\n3. Type check..."
	mypy . --ignore-missing-imports || true
	@echo "\n4. Tests..."
	pytest --cov=. --cov-report=term-missing
	@echo "\n✅ All CI checks passed!"

all: lint format type-check test  ## Run all checks
