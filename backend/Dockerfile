# spell-checker: ignore healthchecks, PYTHONUNBUFFERED, PYTHONDONTWRITEBYTECODE

FROM python:3.14-slim AS runtime-base

# Install curl for healthchecks, create non-root user for all runtime stages
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    useradd --create-home --home-dir /home/appuser --shell /bin/false appuser

ENV VIRTUAL_ENV=/opt/.venv \
    PATH="/opt/.venv/bin:$PATH" \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

FROM runtime-base AS uv-base

COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/.venv

# ── Dependency Layers ─────────────────────────────────────────────────────────
FROM uv-base AS deps-base

COPY pyproject.toml uv.lock ./

FROM deps-base AS dev-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --group dev --no-install-project

FROM deps-base AS prod-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM deps-base AS db-migrations-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group db-migrations --no-install-project

FROM deps-base AS db-seed-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --group db-seed --no-install-project

FROM deps-base AS db-translate-deps

RUN --mount=type=cache,target=/root/.cache/uv \
    UV_COMPILE_BYTECODE=0 uv sync --frozen --only-group db-translate --no-install-project

# ── Source Layers ─────────────────────────────────────────────────────────────
FROM runtime-base AS app-source

COPY app ./app

FROM app-source AS migrations-source

COPY alembic ./alembic
COPY alembic.ini ./

FROM app-source AS seed-source

COPY scripts/seed_data.py ./scripts/seed_data.py
COPY scripts/seed_data.yaml ./scripts/seed_data.yaml

FROM runtime-base AS translate-source

COPY scripts/auto_translate_seed_data.py ./scripts/auto_translate_seed_data.py
COPY scripts/seed_data.yaml ./scripts/seed_data.yaml
COPY translation ./translation

# ── Dev ───────────────────────────────────────────────────────────────────────
FROM runtime-base AS dev

COPY --from=dev-deps /opt/.venv /opt/.venv
COPY . .

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ── Prod ──────────────────────────────────────────────────────────────────────
FROM runtime-base AS prod

COPY --chown=appuser:appuser --from=prod-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=app-source /app /app

USER appuser

ENV SERVER_HOST=0.0.0.0

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# ── DB Ops ────────────────────────────────────────────────────────────────────
FROM runtime-base AS db-migrations

COPY --chown=appuser:appuser --from=db-migrations-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=migrations-source /app /app

USER appuser

CMD ["alembic", "upgrade", "head"]

FROM runtime-base AS db-seed

COPY --chown=appuser:appuser --from=db-seed-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=seed-source /app /app

USER appuser

CMD ["python", "scripts/seed_data.py"]

FROM runtime-base AS db-translate

COPY --chown=appuser:appuser --from=db-translate-deps /opt/.venv /opt/.venv
COPY --chown=appuser:appuser --from=translate-source /app /app

USER appuser

CMD ["python", "scripts/auto_translate_seed_data.py"]
