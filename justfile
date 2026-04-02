set shell := ["zsh", "-euo", "pipefail", "-c"]
set dotenv-load := true

# List available recipes
default:
    @just --list

# ── Dev ───────────────────────────────────────────────────────────────────────

# Start everything: infra + backend + frontend
[group('dev')]
dev: up
    pnpm --dir frontend run dev:web &
    cd backend && uv run uvicorn app.main:app --reload --port 8000

# Start only the frontend Vite dev server
[group('dev')]
dev-frontend:
    pnpm --dir frontend run dev:web

# Start only the backend API server
[group('dev')]
dev-backend:
    cd backend && uv run uvicorn app.main:app --reload --port 8000

# ── Docker ────────────────────────────────────────────────────────────────────

# Start Docker services (postgres + redis)
[group('docker')]
up:
    docker compose up -d

# Stop Docker services
[group('docker')]
down:
    docker compose down

# Stop Docker services and remove volumes (destructive!)
[confirm("This will delete all local database data. Continue? (y/n)")]
[group('docker')]
down-clean:
    docker compose down -v

# ── Test ──────────────────────────────────────────────────────────────────────

# Run all tests (frontend unit + backend)
[group('test')]
test: test-frontend test-backend

# Run frontend unit tests
[group('test')]
test-frontend:
    pnpm --dir frontend run test:unit -- --run

# Run frontend e2e tests (requires dev server running)
[group('test')]
test-e2e:
    pnpm --dir frontend run test:e2e

# Run backend tests
[group('test')]
test-backend:
    cd backend && uv run pytest -x --tb=short

# Run backend tests with coverage report
[group('test')]
test-cov:
    cd backend && uv run pytest --cov=app --cov-report=html --cov-report=term-missing

# ── Lint & Format ─────────────────────────────────────────────────────────────

# Lint everything
[group('lint')]
lint: lint-frontend lint-backend

# Lint frontend
[group('lint')]
lint-frontend:
    pnpm --dir frontend run lint

# Lint backend (ruff)
[group('lint')]
lint-backend:
    cd backend && uv run ruff check . --fix

# Format everything
[group('lint')]
format: format-frontend format-backend

# Format frontend (prettier)
[group('lint')]
format-frontend:
    pnpm --dir frontend run format

# Format backend (ruff)
[group('lint')]
format-backend:
    cd backend && uv run ruff format .

# ── Build ─────────────────────────────────────────────────────────────────────

# Build frontend for production
[group('build')]
build:
    pnpm --dir frontend run build

# Type-check frontend
[group('build')]
type-check:
    pnpm --dir frontend run type-check

# ── Database ──────────────────────────────────────────────────────────────────

# Run all pending database migrations
[group('db')]
migrate:
    cd backend && uv run alembic upgrade head

# Create a new migration (usage: just migrate-new "add user table")
[group('db')]
migrate-new name:
    cd backend && uv run alembic revision --autogenerate -m "{{ name }}"

# Seed the database with card deck data
[group('db')]
seed:
    cd backend && uv run python scripts/seed_data.py

# ── Install ───────────────────────────────────────────────────────────────────

# Install all dependencies
[group('install')]
install: install-frontend install-backend

# Install all dependencies (root + frontend via pnpm workspaces + backend)
[group('install')]
install-frontend:
    pnpm install

# Install backend Python dependencies
[group('install')]
install-backend:
    cd backend && uv sync --all-groups
