"""Category catalog and scoring routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.categories.schemas import CategoryListItem, GuessScoreRequest, GuessScoreResponse, LocaleAvailabilityItem
from app.categories.service import list_categories, list_locale_availability, score_guess_request
from app.core.database import AsyncSessionDep
from app.core.types import Difficulty, LanguageCode

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryListItem])
async def get_categories(
    db: AsyncSessionDep,
    difficulty: Difficulty | None = None,
    language: LanguageCode | None = "en",
) -> list[CategoryListItem]:
    """Get all categories, optionally filtered by difficulty and language."""
    return await list_categories(db, difficulty=difficulty, language=language)


@router.get("/categories/locales", response_model=list[LocaleAvailabilityItem])
async def get_category_locale_availability(
    db: AsyncSessionDep,
    difficulty: Difficulty | None = None,
) -> list[LocaleAvailabilityItem]:
    """Get supported locales with category coverage counts."""
    return await list_locale_availability(db, difficulty=difficulty)


@router.post("/score/guesses", response_model=GuessScoreResponse)
async def score_guesses(request: GuessScoreRequest) -> GuessScoreResponse:
    """Score player guesses using fuzzy matching."""
    return score_guess_request(request)
