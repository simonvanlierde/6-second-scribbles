"""Tests for the database seed script."""

from __future__ import annotations

import copy
import logging
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.categories.models import Category, CategoryPrompt, Prompt
from app.core import redis as redis_module
from app.users.models import User
from scripts import seed_data

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

STARTING_SEED_LOG = "Starting database seed"
SEEDED_DATABASE_LOG = "Seeded database with"
POPULATED_PROMPT_LIBRARY_LOG = "Populated Prompt Library"
MAKING_NO_CHANGES_LOG = "making no changes"
CLEARING_DATABASE_LOG = "Clearing database"
DATABASE_CLEARED_LOG = "Database cleared"
SYSTEM_SOURCE = "system"
EDITED_PROMPT = "cat"
EDITED_LABEL = "kitty"
REMOVED_PROMPT = "dog"
ADDED_PROMPT = "axolotl"
GROWN_CATEGORY = "animals"


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
        assert POPULATED_PROMPT_LIBRARY_LOG in caplog.text
        assert SEEDED_DATABASE_LOG in caplog.text

        categories_result = await db_session.execute(select(Category))
        categories = categories_result.scalars().all()
        assert len(categories) > 0

        prompts_result = await db_session.execute(select(Prompt))
        prompts = prompts_result.scalars().all()
        assert len(prompts) > 0

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
        assert MAKING_NO_CHANGES_LOG in caplog.text
        categories_result = await db_session.execute(select(Category))
        assert len(categories_result.scalars().all()) == 1

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

    async def test_overwrite_updates_in_place_and_keeps_ids(
        self,
        db_session: AsyncSession,
        redis_client: Redis,
        seed_data_session_maker: None,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Overwrite keeps the IDs rooms hold, applies edits, and drops only what left the YAML."""
        _ = seed_data_session_maker
        await seed_data.seed_database()
        category_ids = dict((await db_session.execute(select(Category.slug, Category.id))).all())
        prompt_ids = dict((await db_session.execute(select(Prompt.stable_key, Prompt.id))).all())
        link_ids = set((await db_session.execute(select(CategoryPrompt.id))).scalars().all())
        await redis_module.cache_localized_scoring_targets(category_ids[GROWN_CATEGORY], "en", [1], {"stale": True})

        data = copy.deepcopy(seed_data.SEED_DATA)
        prompts = data["prompts"]
        categories = data["system_categories"]
        next(p for p in prompts if p["id"] == EDITED_PROMPT)["translations"][0]["label"] = EDITED_LABEL
        data["prompts"] = [p for p in prompts if p["id"] != REMOVED_PROMPT]
        for category in categories:
            category["items"] = [item for item in category["items"] if item != REMOVED_PROMPT]
        data["prompts"].append({"id": ADDED_PROMPT, "translations": [{"locale": "en", "label": ADDED_PROMPT}]})
        animals = next(c for c in categories if c["id"] == GROWN_CATEGORY)
        animals["items"].append(ADDED_PROMPT)
        removed_category = categories.pop()["id"]
        monkeypatch.setattr(seed_data, "SEED_DATA", data)

        await seed_data.seed_database(overwrite=True)
        db_session.expire_all()

        new_category_ids = dict((await db_session.execute(select(Category.slug, Category.id))).all())
        new_prompt_ids = dict((await db_session.execute(select(Prompt.stable_key, Prompt.id))).all())
        assert removed_category not in new_category_ids
        assert new_category_ids == {k: v for k, v in category_ids.items() if k != removed_category}
        assert REMOVED_PROMPT not in new_prompt_ids
        assert ADDED_PROMPT in new_prompt_ids
        del new_prompt_ids[ADDED_PROMPT]
        assert new_prompt_ids == {k: v for k, v in prompt_ids.items() if k != REMOVED_PROMPT}

        cat = (await db_session.execute(select(Prompt).where(Prompt.stable_key == EDITED_PROMPT))).scalar_one()
        assert cat.translations["en"]["label"] == EDITED_LABEL
        linked = (
            (
                await db_session.execute(
                    select(Prompt.stable_key)
                    .join(CategoryPrompt, CategoryPrompt.prompt_id == Prompt.id)
                    .where(CategoryPrompt.category_id == category_ids[GROWN_CATEGORY])
                    .order_by(CategoryPrompt.sort_order)
                )
            )
            .scalars()
            .all()
        )
        assert linked == animals["items"]
        # Links of untouched categories keep their rows; only edited categories are relinked.
        kept_link_ids = set((await db_session.execute(select(CategoryPrompt.id))).scalars().all()) & link_ids
        assert len(kept_link_ids) > len(link_ids) / 2
        assert await redis_client.keys("cat_targets:*") == []
