"""Tests for the database seed script."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.categories.models import Category, Prompt
from app.users.models import User
from scripts import seed_data

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

STARTING_SEED_LOG = "Starting database seed"
SEEDED_DATABASE_LOG = "Seeded database with"
POPULATED_PROMPT_LIBRARY_LOG = "Populated Prompt Library"
CLEARING_DATABASE_LOG = "Clearing database"
DATABASE_CLEARED_LOG = "Database cleared"
SYSTEM_SOURCE = "system"


class TestSeedDataScript:
    """Tests for the seed-data maintenance script."""

    async def test_seed_database_logs_when_it_populates_empty_database(
        self,
        db_session: AsyncSession,
        seed_data_session_maker: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Seeding an empty database should populate content and log progress."""
        _ = seed_data_session_maker
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.seed_database()

        assert STARTING_SEED_LOG in caplog.text
        assert SEEDED_DATABASE_LOG in caplog.text

        categories_result = await db_session.execute(select(Category))
        categories = categories_result.scalars().all()
        assert len(categories) > 0

        prompts_result = await db_session.execute(select(Prompt))
        prompts = prompts_result.scalars().all()
        assert len(prompts) > 0

        users = await db_session.execute(select(User))
        seeded_users = users.scalars().all()
        assert seeded_users == []

        system_categories = [category for category in categories if category.source == SYSTEM_SOURCE]
        assert len(system_categories) == len(categories)
        assert all(isinstance(category.translations, dict) and category.translations for category in system_categories)

    async def test_seed_database_logs_and_skips_when_already_seeded(
        self,
        db_session: AsyncSession,
        seed_data_session_maker: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Seeding an already-populated database should keep existing content."""
        _ = seed_data_session_maker
        db_session.add(Category(difficulty="easy", default_locale="en", source="system", available_locales=["en"]))
        await db_session.commit()
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.seed_database()

        assert STARTING_SEED_LOG in caplog.text
        assert POPULATED_PROMPT_LIBRARY_LOG in caplog.text
        categories_result = await db_session.execute(select(Category))
        assert len(categories_result.scalars().all()) > 1

    async def test_clear_database_logs_when_it_deletes_categories(
        self,
        db_session: AsyncSession,
        seed_data_session_maker: None,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Clearing the database removes categories and users and logs the reset."""
        _ = seed_data_session_maker
        db_session.add(Category(difficulty="easy", default_locale="en", source="system", available_locales=["en"]))
        db_session.add(
            User(
                id="seed-clear-user",
                username="seed_clear_user",
                preferred_locale="en",
                password_hash="hash",  # noqa: S106
            )
        )
        await db_session.commit()
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.clear_database()

        assert CLEARING_DATABASE_LOG in caplog.text
        assert DATABASE_CLEARED_LOG in caplog.text
        categories = await db_session.execute(select(Category))
        users = await db_session.execute(select(User))
        assert categories.scalars().all() == []
        assert users.scalars().all() == []
