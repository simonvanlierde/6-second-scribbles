set shell := ["bash", "-euo", "pipefail", "-O", "nullglob", "-c"]
set dotenv-load := true

# List available recipes.
default:
    @just --list

# ── Dev ───────────────────────────────────────────────────────────────────────

# Start Docker, then the frontend and backend dev servers.
[group('dev')]
dev: up
    just frontend/dev &
    just backend/dev

# Start the local dev stack for Playwright e2e against the real backend.
[group('docker')]
e2e-backend-up:
    docker compose up --build -d database cache database-migrations backend

e2e-backend-down:
    docker compose down

# ── Docker ────────────────────────────────────────────────────────────────────

# Start full dev stack in Docker (infra + backend + frontend hot reload).
[group('docker')]
up:
    docker compose up -d

# Stop full dev stack.
[group('docker')]
down:
    docker compose down

# Stop full dev stack and remove volumes.
[confirm("This will delete all local database data. Continue? (y/n)")]
[group('docker')]
down-clean:
    docker compose down -v

# Start full prod stack in Docker (infra + backend + built frontend).
[group('docker')]
up-prod:
    docker compose -f compose.yml -f compose.prod.yml up -d --build

# Stop full prod stack.
[group('docker')]
down-prod:
    docker compose -f compose.yml -f compose.prod.yml down

# ── Test ──────────────────────────────────────────────────────────────────────

# Run all tests.
[group('test')]
test: test-frontend test-backend

# Run frontend unit tests.
[group('test')]
test-frontend:
    just frontend/test

# Run frontend e2e tests.
[group('test')]
test-e2e:
    just frontend/test-e2e

# Run frontend e2e tests in the Playwright UI.
[group('test')]
test-e2e-ui:
    just frontend/test-e2e-ui

# Run backend tests.
[group('test')]
test-backend:
    just backend/test

# ── Check & Format ────────────────────────────────────────────────────────────

# Check everything.
[group('check')]
check: check-contracts check-frontend check-backend check-root check-security

# Check the frontend.
[group('check')]
check-frontend:
    just frontend/check

# Check the backend.
[group('check')]
check-backend:
    just backend/check

# Check root-level docs and config files.
[group('check')]
check-root:
    pnpm run check

# Scan the repository for secrets.
[group('check')]
check-security:
    gitleaks detect --redact --no-banner

# Format everything.
[group('format')]
format: format-root format-frontend format-backend

# Format root-level docs and config files.
[group('format')]
format-root:
    pnpm run format

# Format the frontend.
[group('format')]
format-frontend:
    just frontend/format

# Format the backend.
[group('format')]
format-backend:
    just backend/format

# ── Build ─────────────────────────────────────────────────────────────────────

# Build the frontend.
[group('build')]
build:
    just frontend/build

# ── Contracts ─────────────────────────────────────────────────────────────────

# Generate all contract artifacts.
[group('contracts')]
generate-contracts:
    just backend/generate-contracts
    pnpm exec biome format --write --config-path . contracts/openapi.json contracts/room-events.json contracts/jsonschema
    just frontend/generate-contracts

# Validate that all tracked contract artifacts are reproducible.
[group('check')]
check-contracts:
    pnpm run contracts:check
    pnpm --dir frontend run type-check

# ── Database ──────────────────────────────────────────────────────────────────

# Run all pending database migrations.
[group('db')]
migrate:
    just backend/migrate

# Create a new migration.
[group('db')]
migrate-new name:
    just backend/migrate-new "{{ name }}"

# Seed the database with card deck data.
[group('db')]
seed:
    just backend/seed

# ── Install ───────────────────────────────────────────────────────────────────

# Install all dependencies.
[group('install')]
install: install-frontend install-backend

# Install frontend dependencies.
[group('install')]
install-frontend:
    just frontend/install

# Install backend dependencies.
[group('install')]
install-backend:
    just backend/install
