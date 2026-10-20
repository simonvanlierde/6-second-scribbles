"""Category catalog routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.categories.schemas import LocaleAvailabilityItem
from app.categories.service import list_locale_availability
from app.core.database import AsyncSessionDep
from app.core.types import Difficulty

router = APIRouter(tags=["categories"])


@router.get("/categories/locales", response_model=list[LocaleAvailabilityItem])
async def get_category_locale_availability(
    db: AsyncSessionDep,
    difficulty: Difficulty | None = None,
) -> list[LocaleAvailabilityItem]:
    """Get supported locales with category coverage counts."""
    return await list_locale_availability(db, difficulty=difficulty)
