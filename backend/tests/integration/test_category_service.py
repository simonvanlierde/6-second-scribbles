"""Integration tests for category service helpers that need real database state."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.categories import service as category_service
from app.categories.models import Category, Prompt
from tests.constants import ANIMALS

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

FALLBACK = "Fallback"


class TestCategoryService:
    """Focused tests for CategoryService methods."""

    @pytest.mark.usefixtures("_deterministic_sample")
    async def test_select_and_deal_returns_localized_items(self, db_session: AsyncSession) -> None:
        """Return localized category sets with alternatives."""
        category = Category(
            difficulty="medium",
            source="system",
            available_locales=["en"],
            translations={"en": {"name": "Animals"}},
        )
        db_session.add(category)
        await db_session.flush()

        cat_prompt = Prompt(stable_key="cat", translations={"en": {"label": "cat", "aliases": ["kitty"]}})
        dog_prompt = Prompt(stable_key="dog", translations={"en": {"label": "dog", "aliases": []}})
        db_session.add(cat_prompt)
        db_session.add(dog_prompt)
        await db_session.flush()

        db_session.add(category_service.CategoryPrompt(category_id=category.id, prompt_id=cat_prompt.id, sort_order=1))
        db_session.add(category_service.CategoryPrompt(category_id=category.id, prompt_id=dog_prompt.id, sort_order=2))
        await db_session.commit()

        category_ids = await category_service.select_category_ids(
            db_session, difficulty="medium", player_count=1, locales=["en"], room_locale="en"
        )
        card = await category_service.deal_category(
            db_session, category_id=category_ids[0], preferred_locale="en", fallback_locale="en"
        )

        assert category_ids == [category.id]
        assert card.category == ANIMALS
        assert card.items == ["cat", "dog"]
        assert card.alternatives["cat"] == ["kitty"]

    @pytest.mark.usefixtures("_deterministic_sample")
    async def test_select_and_deal_fall_back_to_english(self, db_session: AsyncSession) -> None:
        """Selection and dealing fall back to English when the requested locale is not available."""
        category = Category(
            difficulty="medium",
            source="system",
            available_locales=["en"],
            translations={"en": {"name": FALLBACK}},
        )
        prompt = Prompt(stable_key="tree", translations={"en": {"label": "tree", "aliases": []}})
        db_session.add(category)
        db_session.add(prompt)
        await db_session.flush()
        db_session.add(category_service.CategoryPrompt(category_id=category.id, prompt_id=prompt.id, sort_order=1))
        await db_session.commit()

        category_ids = await category_service.select_category_ids(
            db_session, difficulty="medium", player_count=1, locales=["es"], room_locale="es"
        )
        card = await category_service.deal_category(
            db_session, category_id=category_ids[0], preferred_locale="es", fallback_locale="es"
        )

        assert category_ids == [category.id]
        assert card.category == FALLBACK
