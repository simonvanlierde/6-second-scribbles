"""HTTP schemas for the category and scoring domain (M2M Refactor)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.types import Difficulty, LanguageCode


class CategoryListItem(BaseModel):
    """Compact localized category representation used by list endpoints."""

    id: int
    name: str
    difficulty: Difficulty
    locale: LanguageCode | None


class SelectedCategorySet(BaseModel):
    """One selected localized category set for game setup."""

    category_id: int
    category_name: str
    item_ids: list[int]
    items: list[str]
    alternatives: dict[str, list[str]]


class CategorySelectionRequest(BaseModel):
    """Parameters for selecting category sets for a room/game."""

    difficulty: Difficulty
    count: int = Field(default=1, ge=1)
    player_count: int = Field(default=2, ge=1)
    locale: LanguageCode = "en"
    locales: list[LanguageCode] = Field(default_factory=list)


class CategorySelectionResponse(BaseModel):
    """Response for room-scoped category selection."""

    difficulty: Difficulty
    selections: list[SelectedCategorySet]


class LocaleAvailabilityItem(BaseModel):
    """Aggregated locale support across selectable system categories."""

    locale: LanguageCode
    category_count: int
    difficulty_counts: dict[str, int] = Field(default_factory=dict)
