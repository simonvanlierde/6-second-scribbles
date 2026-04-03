set shell := ["bash", "-euo", "pipefail", "-c"]
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

# ── Docker ────────────────────────────────────────────────────────────────────

# Start infra only (PostgreSQL + Redis) — used by `just dev` for local backend development.
[group('docker')]
up:
    docker compose up -d

# Stop infra services.
[group('docker')]
down:
    docker compose down

# Stop infra services and remove volumes.
[confirm("This will delete all local database data. Continue? (y/n)")]
[group('docker')]
down-clean:
    docker compose down -v

# Start full dev stack in Docker (infra + backend with hot reload).
[group('docker')]
up-dev:
    docker compose -f compose.yml -f compose.dev.yml up -d --build

# Stop full dev stack.
[group('docker')]
down-dev:
    docker compose -f compose.yml -f compose.dev.yml down

# Start full prod stack in Docker (infra + backend, optimized build).
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

# Backwards-compatible alias for users who prefer the pluralized recipe name.
[group('test')]
tests-e2e-ui:
    just test-e2e-ui

# Run backend tests.
[group('test')]
test-backend:
    just backend/test

# ── Check & Format ────────────────────────────────────────────────────────────

# Check everything.
[group('check')]
check: check-contracts check-frontend check-backend

# Check the frontend.
[group('check')]
check-frontend:
    just frontend/check

# Check the backend.
[group('check')]
check-backend:
    just backend/check

# Format everything.
[group('format')]
format: format-frontend format-backend

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

# Generate shared websocket contract artifacts.
[group('contracts')]
contracts:
    npm run contracts:types

# Generate and validate shared websocket contract artifacts.
[group('contracts')]
validate-contracts:
    npm run contracts:validate

# Validate that contract-related generated files are up to date.
[group('check')]
check-contracts:
    npm run contracts:check

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
