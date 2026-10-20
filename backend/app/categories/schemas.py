"""HTTP schemas for the category and scoring domain (M2M Refactor)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.types import LanguageCode


class LocaleAvailabilityItem(BaseModel):
    """Aggregated locale support across selectable system categories."""

    locale: LanguageCode
    category_count: int
    difficulty_counts: dict[str, int] = Field(default_factory=dict)
