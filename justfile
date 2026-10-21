set shell := ["bash", "-euo", "pipefail", "-O", "nullglob", "-c"]
set dotenv-load := true

# Every compose invocation names its files explicitly. This repo's .env sets
# COMPOSE_FILE so that Dockge's flagless `docker compose up -d` gets prod config;
# that also makes a bare `docker compose` here mean prod, which is not what a
# recipe called `dev-*` or `down-clean` should ever touch.
dev_compose := "docker compose -f compose.yml -f compose.dev.yml"
prod_compose := "docker compose -f compose.yml -f compose.prod.yml"
# Prod build and limits under a throwaway project name, so a load test never
# touches a real stack; container names start with tmp- to mark them disposable.
loadtest_compose := "docker compose -p tmp-6ss-load --profile db-seed -f compose.yml -f compose.prod.yml -f backend/loadtest/compose.yml"

# List available recipes.
default:
    @just --list

# ── Dev ───────────────────────────────────────────────────────────────────────

# Start local frontend/backend dev servers against Dockerized infra.
[group('dev')]
dev: dev-infra-up
    just frontend/dev &
    just backend/dev

# Start only the infrastructure needed for local development.
[group('dev')]
dev-infra-up:
    {{ dev_compose }} up -d database cache
    {{ dev_compose }} run --rm --build database-migrations

# Stop the infrastructure used by local development.
[group('dev')]
dev-down:
    {{ dev_compose }} stop database cache

# Start the local dev stack for Playwright e2e against the real backend.
[group('docker')]
e2e-backend-up:
    {{ dev_compose }} up --build -d database cache database-migrations backend

e2e-backend-down:
    {{ dev_compose }} down

# ── Docker ────────────────────────────────────────────────────────────────────

# Start full dev stack in Docker (infra + backend + frontend hot reload).
[group('docker')]
up:
    {{ dev_compose }} up -d

# Stop full dev stack.
[group('docker')]
down:
    {{ dev_compose }} down

# Stop full dev stack and remove volumes.
[confirm("This will delete all local database data. Continue? (y/n)")]
[group('docker')]
down-clean:
    {{ dev_compose }} down -v

# Start full prod stack in Docker (infra + backend + built frontend).
# --pull fetches new base images, so their security fixes reach the build.
[group('docker')]
up-prod:
    {{ prod_compose }} build --pull
    {{ prod_compose }} pull --ignore-buildable
    {{ prod_compose }} up -d

# Stop full prod stack.
[group('docker')]
down-prod:
    {{ prod_compose }} down

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

# Harness flags pass through, e.g. `just loadtest --smoke`; see docs/capacity.md.
# Measure WebSocket capacity under the prod CPU/memory limits.
[group('test')]
loadtest *args:
    #!/usr/bin/env bash
    set -euo pipefail
    trap '{{ loadtest_compose }} down -v --rmi local' EXIT
    {{ loadtest_compose }} up -d --build --wait backend
    {{ loadtest_compose }} run --rm --build --name tmp-6ss-load-seed database-seed
    just backend/loadtest --url "ws://127.0.0.1:${LOADTEST_PORT:-18000}" --container tmp-6ss-load-backend-1 {{ args }}

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

# Scan the full git history for secrets (Dockerized Betterleaks). The checkout and
# git's shared directory are both mounted at their real paths: in a linked worktree,
# .git is a file pointing at the main checkout's .git, so mounting the checkout alone
# leaves git with no repository. Known dev and test passwords are listed in
# .betterleaksignore.
[group('check')]
check-security:
    docker run --rm --user "$(id -u):$(id -g)" \
        -v "$(pwd)":"$(pwd)" -w "$(pwd)" \
        -v "$(git rev-parse --path-format=absolute --git-common-dir)":"$(git rev-parse --path-format=absolute --git-common-dir)" \
        ghcr.io/betterleaks/betterleaks:v1.9.0 \
        git --config .betterleaks.toml --redact --no-banner

# Run every git hook over the whole repo, not just staged files (CI runs them too).
[group('check')]
hooks:
    prek run -a

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
    pnpm exec biome format --write --config-path . contracts/openapi.json contracts/jsonschema
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

# Bump all dependencies to their latest versions.
[group('install')]
bump: bump-root bump-frontend bump-backend

# Bump root-level dependencies.
[group('install')]
bump-root:
    pnpm update --latest

# Bump frontend dependencies.
[group('install')]
bump-frontend:
    just frontend/bump

# Bump backend dependencies.
[group('install')]
bump-backend:
    just backend/bump
