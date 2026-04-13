"""Tests for the database seed script."""

from __future__ import annotations

import logging

from sqlalchemy import select

from app.categories.models import Category, Prompt
from app.users.models import User
from scripts import seed_data


class TestSeedDataScript:
    async def test_seed_database_logs_when_it_populates_empty_database(self, test_db, caplog) -> None:
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.seed_database()

        assert "Starting database seed" in caplog.text
        assert "Seeded database with" in caplog.text

        categories_result = await test_db.execute(select(Category))
        categories = categories_result.scalars().all()
        assert len(categories) > 0

        prompts_result = await test_db.execute(select(Prompt))
        prompts = prompts_result.scalars().all()
        assert len(prompts) > 0

        users = await test_db.execute(select(User))
        seeded_users = users.scalars().all()
        assert seeded_users == []

        system_categories = [category for category in categories if category.source == "system"]
        assert len(system_categories) == len(categories)
        assert all(isinstance(category.translations, dict) and category.translations for category in system_categories)

    async def test_seed_database_logs_and_skips_when_already_seeded(self, test_db, caplog) -> None:
        test_db.add(Category(difficulty="easy", default_locale="en", source="system", available_locales=["en"]))
        await test_db.commit()
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.seed_database()

        assert "Starting database seed" in caplog.text
        assert "Populated Prompt Library" in caplog.text
        categories_result = await test_db.execute(select(Category))
        assert len(categories_result.scalars().all()) > 1

    async def test_clear_database_logs_when_it_deletes_categories(self, test_db, caplog) -> None:
        test_db.add(Category(difficulty="easy", default_locale="en", source="system", available_locales=["en"]))
        test_db.add(
            User(
                id="seed-clear-user",
                username="seed_clear_user",
                preferred_locale="en",
                password_hash="hash",  # noqa: S106
            )
        )
        await test_db.commit()
        caplog.set_level(logging.INFO, logger="scripts.seed_data")

        await seed_data.clear_database()

        assert "Clearing database" in caplog.text
        assert "Database cleared" in caplog.text
        categories = await test_db.execute(select(Category))
        users = await test_db.execute(select(User))
        assert categories.scalars().all() == []
        assert users.scalars().all() == []
