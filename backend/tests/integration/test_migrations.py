"""Migrations run both ways against a real Postgres."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import pytest
from alembic import command
from sqlalchemy import text

from app.core import database

if TYPE_CHECKING:
    from alembic.config import Config

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

BEFORE_DROP_INDEXES = "b2a7f484d1a9"
DROPPED_INDEXES = {
    "idx_users_username",
    "idx_prompt_stable_key",
    "idx_category_prompt_category",
    "idx_users_preferred_locale",
    "idx_category_translations",
    "idx_prompt_translations",
}


async def _present_indexes() -> set[str]:
    async with database.get_session_maker()() as session:
        rows = await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE indexname = ANY(:names)"),
            {"names": sorted(DROPPED_INDEXES)},
        )
        return set(rows.scalars())


async def test_drop_redundant_indexes_downgrades_and_upgrades(alembic_config: Config) -> None:
    """Downgrading the index cleanup restores all six indexes, and upgrading drops them again."""
    assert await _present_indexes() == set()

    await asyncio.to_thread(command.downgrade, alembic_config, BEFORE_DROP_INDEXES)
    try:
        assert await _present_indexes() == DROPPED_INDEXES
    finally:
        await asyncio.to_thread(command.upgrade, alembic_config, "head")

    assert await _present_indexes() == set()
