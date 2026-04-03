"""Helpers for running Alembic migrations from Python."""

from __future__ import annotations

import asyncio
from pathlib import Path

from alembic.config import Config

from alembic import command
from app.core.config import settings

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_ALEMBIC_INI_PATH = _BACKEND_ROOT / "alembic.ini"
_ALEMBIC_SCRIPT_PATH = _BACKEND_ROOT / "alembic"


def _build_alembic_config() -> Config:
    config = Config(str(_ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(_ALEMBIC_SCRIPT_PATH))
    config.set_main_option("prepend_sys_path", str(_BACKEND_ROOT))
    config.set_main_option("sqlalchemy.url", settings.database_url)
    return config


def upgrade_database(revision: str = "head") -> None:
    """Apply Alembic migrations up to the requested revision."""
    command.upgrade(_build_alembic_config(), revision)


async def run_migrations(revision: str = "head") -> None:
    """Run Alembic migrations without blocking the active event loop."""
    await asyncio.to_thread(upgrade_database, revision)
