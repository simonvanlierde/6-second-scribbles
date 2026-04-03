"""HTTP schemas for the category and scoring domain."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel, Field

from app.core.types import Difficulty, LanguageCode  # noqa: TC001 - used by Pydantic at runtime
from app.scoring.models import GuessMatchDetailResult  # noqa: TC001 - used by Pydantic at runtime

if TYPE_CHECKING:
    from app.categories.models import Card, Category


class GuessRequest(BaseModel):
    """Request body for scoring player guesses."""

    guesses: list[str]
    correct_answers: list[str]
    alternatives: dict[str, list[str]] = Field(default_factory=dict)


class GuessResponse(BaseModel):
    """Response body for scoring player guesses."""

    score: int
    total: int
    percentage: float
    matches: list[GuessMatchDetailResult]
    unmatched_answers: list[str]


class CategorySummary(BaseModel):
    """Compact category representation used by list endpoints."""

    id: int
    name: str
    difficulty: Difficulty
    description: str | None
    language: LanguageCode | None
    room_id: str | None
    created_by: str | None
    is_custom: bool

    @classmethod
    def from_model(cls, category: Category) -> CategorySummary:
        """Build a category summary from a Category ORM instance."""
        return cls(
            id=category.id,
            name=category.name,
            difficulty=cast("Difficulty", category.difficulty),
            description=category.description,
            language=cast("LanguageCode", category.language),
            room_id=category.room_id,
            created_by=category.created_by,
            is_custom=category.room_id is not None,
        )


class CardResponse(BaseModel):
    """Card representation returned from category detail endpoints."""

    id: int
    category_id: int
    item: str
    alternatives: list[str]

    @classmethod
    def from_model(cls, card: Card) -> CardResponse:
        """Build a card response from a Card ORM instance."""
        return cls(
            id=card.id,
            category_id=card.category_id,
            item=card.item,
            alternatives=card.alternatives or [],
        )


class CategoriesResponse(BaseModel):
    """Response for listing categories."""

    categories: list[CategorySummary]
    count: int


class CategoryDetailResponse(BaseModel):
    """Response for a single category and its cards."""

    category: CategorySummary
    items: list[str]
    cards: list[CardResponse]


class RandomCategoryCardSet(BaseModel):
    """Cards selected for a single player/category pairing."""

    category: str
    items: list[str]
    alternatives: dict[str, list[str]]
    is_custom: bool


class RandomCardsResponse(BaseModel):
    """Response for the random card selection endpoint."""

    difficulty: Difficulty
    categories: dict[int, RandomCategoryCardSet]
    includes_custom: bool
