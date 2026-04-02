"""Category, card, and scoring routes."""

from __future__ import annotations

from fastapi import APIRouter

from app.api_schemas import (
    CategoriesResponse,
    CategoryDetailResponse,
    GuessRequest,
    GuessResponse,
    RandomCardsResponse,
)
from app.database import AsyncSessionDep  # noqa: TC001 - FastAPI resolves this dependency alias at runtime
from app.domain_types import Difficulty, LanguageCode  # noqa: TC001 - FastAPI uses these runtime annotations
from app.services.category_service import (
    get_category_detail,
    get_random_category_cards,
    list_categories,
    score_guess_request,
)

router = APIRouter()


@router.get("/api/categories", response_model=CategoriesResponse)
async def get_categories(
    db: AsyncSessionDep,
    difficulty: Difficulty | None = None,
    language: LanguageCode | None = "en",
) -> CategoriesResponse:
    """Get all categories, optionally filtered by difficulty and language."""
    return await list_categories(db, difficulty=difficulty, language=language)


@router.get("/api/categories/{category_id}", response_model=CategoryDetailResponse)
async def get_category(category_id: int, db: AsyncSessionDep) -> CategoryDetailResponse:
    """Get a specific category with its items."""
    return await get_category_detail(db, category_id=category_id)


@router.get("/api/cards/random", response_model=RandomCardsResponse)
async def get_random_cards(
    db: AsyncSessionDep,
    difficulty: Difficulty = "medium",
    count: int = 1,
    player_count: int = 2,
    room_id: str | None = None,
    language: LanguageCode = "en",
) -> RandomCardsResponse:
    """Get random cards for a game."""
    return await get_random_category_cards(
        db,
        difficulty=difficulty,
        count=count,
        player_count=player_count,
        room_id=room_id,
        language=language,
    )


@router.post("/api/score/guesses", response_model=GuessResponse)
async def score_guesses(request: GuessRequest) -> GuessResponse:
    """Score player guesses using fuzzy matching."""
    return score_guess_request(request)
