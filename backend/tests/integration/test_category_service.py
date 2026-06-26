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

    async def test_list_categories_filters_by_difficulty_and_language(self, db_session: AsyncSession) -> None:
        """Filter categories by difficulty and language."""
        db_session.add(
            Category(
                difficulty="easy",
                source="system",
                available_locales=["en"],
                translations={"en": {"name": "Easy EN"}},
            )
        )
        db_session.add(
            Category(
                difficulty="easy",
                source="system",
                available_locales=["fr"],
                translations={"fr": {"name": "Facile FR"}},
            )
        )
        db_session.add(
            Category(
                difficulty="hard",
                source="system",
                available_locales=["en"],
                translations={"en": {"name": "Hard EN"}},
            )
        )
        await db_session.commit()

        response = await category_service.list_categories(db_session, difficulty="easy", language="en")

        assert len(response) == 1
        assert [category.name for category in response] == ["Easy EN"]

    @pytest.mark.usefixtures("_deterministic_sample")
    async def test_select_category_sets_returns_localized_items(self, db_session: AsyncSession) -> None:
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

        response = await category_service.select_category_sets(
            db_session,
            difficulty="medium",
            count=1,
            player_count=1,
            locale="en",
            locales=["en"],
        )

        assert len(response.selections) == 1
        selection = response.selections[0]
        assert selection.category_name == ANIMALS
        assert selection.items == ["cat", "dog"]
        assert selection.alternatives["cat"] == ["kitty"]

    @pytest.mark.usefixtures("_deterministic_sample")
    async def test_select_category_sets_falls_back_to_english(self, db_session: AsyncSession) -> None:
        """Test that select_category_sets falls back to English when the requested locale is not available."""
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

        response = await category_service.select_category_sets(
            db_session,
            difficulty="medium",
            count=1,
            player_count=1,
            locale="es",
            locales=["es"],
        )

        assert len(response.selections) == 1
        assert response.selections[0].category_name == FALLBACK
