"""Category-related business logic shared by HTTP routes."""

from __future__ import annotations

import random
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select

from app.categories.models import Card, Category
from app.categories.schemas import (
    CardResponse,
    CategoriesResponse,
    CategoryDetailResponse,
    CategorySummary,
    GuessRequest,
    GuessResponse,
    RandomCardsResponse,
    RandomCategoryCardSet,
)
from app.core.types import Difficulty, LanguageCode  # noqa: TC001 - used in runtime annotations
from app.scoring import guess_matcher

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def list_categories(
    db: AsyncSession,
    *,
    difficulty: Difficulty | None,
    language: LanguageCode | None,
) -> CategoriesResponse:
    """List categories, optionally filtered by difficulty and language."""
    query = select(Category)

    if difficulty:
        query = query.where(Category.difficulty == difficulty.lower())

    if language:
        query = query.where(Category.language == language.lower())

    result = await db.execute(query)
    categories = result.scalars().all()

    return CategoriesResponse(
        categories=[CategorySummary.from_model(category) for category in categories],
        count=len(categories),
    )


async def get_category_detail(db: AsyncSession, *, category_id: int) -> CategoryDetailResponse:
    """Return one category with its cards."""
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    cards_result = await db.execute(select(Card).where(Card.category_id == category_id))
    cards = cards_result.scalars().all()

    return CategoryDetailResponse(
        category=CategorySummary.from_model(category),
        items=[card.item for card in cards],
        cards=[CardResponse.from_model(card) for card in cards],
    )


async def get_random_category_cards(
    db: AsyncSession,
    *,
    difficulty: Difficulty,
    count: int,
    player_count: int,
    room_id: str | None,
    language: LanguageCode,
) -> RandomCardsResponse:
    """Select random category card sets for a game."""
    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.language == language.lower(),
        Category.room_id.is_(None),
    )
    result = await db.execute(query)
    categories = list(result.scalars().all())

    if room_id:
        custom_query = select(Category).where(Category.room_id == room_id)
        custom_result = await db.execute(custom_query)
        categories.extend(list(custom_result.scalars().all()))

    if not categories:
        raise HTTPException(status_code=404, detail=f"No categories found for difficulty: {difficulty}")

    total_needed = count * player_count
    if len(categories) < total_needed:
        raise HTTPException(
            status_code=400,
            detail=f"Not enough categories ({len(categories)}) for {player_count} players and {count} rounds. "
            f"Available: {len(categories)}, needed: {total_needed}",
        )

    selected_categories = random.sample(categories, total_needed)
    selected_ids = [category.id for category in selected_categories]
    all_cards_result = await db.execute(select(Card).where(Card.category_id.in_(selected_ids)))
    cards_by_cat_id: dict[int, list[Card]] = {}
    for card in all_cards_result.scalars().all():
        cards_by_cat_id.setdefault(card.category_id, []).append(card)

    cards_by_category: dict[int, RandomCategoryCardSet] = {}
    for category in selected_categories:
        cards = cards_by_cat_id.get(category.id, [])
        cards_by_category[category.id] = RandomCategoryCardSet(
            category=category.name,
            items=[card.item for card in cards],
            alternatives={card.item: card.alternatives or [] for card in cards},
            is_custom=category.room_id is not None,
        )

    return RandomCardsResponse(
        difficulty=difficulty,
        categories=cards_by_category,
        includes_custom=room_id is not None,
    )


def score_guess_request(request: GuessRequest) -> GuessResponse:
    """Score a guess request using the shared matcher."""
    result = guess_matcher.score_guesses(
        guesses=request.guesses,
        correct_answers=request.correct_answers,
        alternatives_map=request.alternatives,
    )

    return GuessResponse(
        score=result.score,
        total=result.total,
        percentage=result.percentage,
        matches=result.matches,
        unmatched_answers=result.unmatched_answers,
    )
