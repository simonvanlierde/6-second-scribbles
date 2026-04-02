"""Helpers for converting ORM models into typed API schemas."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.api_schemas import CardResponse, CategorySummary, RoomCategoriesItem

if TYPE_CHECKING:
    from app.db_models import Card, Category


def category_summary_from_model(category: Category) -> CategorySummary:
    """Build a category summary schema from a Category ORM instance."""
    return CategorySummary(
        id=category.id,
        name=category.name,
        difficulty=category.difficulty,
        description=category.description,
        language=category.language,
        room_id=category.room_id,
        created_by=category.created_by,
        is_custom=category.room_id is not None,
    )


def card_response_from_model(card: Card) -> CardResponse:
    """Build a card response schema from a Card ORM instance."""
    return CardResponse(
        id=card.id,
        category_id=card.category_id,
        item=card.item,
        alternatives=card.alternatives or [],
    )


def room_categories_item_from_model(category: Category, *, items: list[str]) -> RoomCategoriesItem:
    """Build a room-category response item from a Category ORM instance."""
    return RoomCategoriesItem(
        **category_summary_from_model(category).model_dump(),
        items=items,
    )
