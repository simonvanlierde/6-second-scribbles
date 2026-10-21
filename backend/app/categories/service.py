"""Category catalog and selection logic shared by HTTP routes (M2M + Denormalize Refactor)."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.categories.models import Category, CategoryPrompt, Prompt, normalize_locale_code
from app.categories.schemas import LocaleAvailabilityItem
from app.core import redis
from app.rooms.state import PlayerPromptAssignmentState
from app.scoring import GuessTarget

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import Difficulty, LanguageCode


@dataclass(frozen=True)
class LocalizedScoringTargets:
    """Localized scoring targets for one assigned category prompt."""

    category_id: int
    category_name: str
    targets: list[GuessTarget]


SYSTEM_CATEGORY_SOURCE = "system"
DEFAULT_LANGUAGE_CODE = "en"


def _normalize_locale(locale: LanguageCode | str | None) -> str:
    normalized = normalize_locale_code(locale or DEFAULT_LANGUAGE_CODE)
    return normalized or DEFAULT_LANGUAGE_CODE


def _locales(category: Category) -> set[str]:
    """The category's playable locales, normalized."""
    return {normalized for raw in category.available_locales if (normalized := normalize_locale_code(raw))}


def _normalize_locale_list(locales: list[LanguageCode | str] | None, *, fallback: str) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for raw in locales or []:
        loc = _normalize_locale(raw)
        if loc and loc not in seen:
            ordered.append(loc)
            seen.add(loc)
    if fallback not in seen:
        ordered.append(fallback)
    return ordered


async def _get_visible_category_or_404(
    db: AsyncSession,
    *,
    category_id: int,
) -> Category:
    result = await db.execute(select(Category).where(Category.id == category_id))
    category = result.scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category


async def _load_category_prompts(
    db: AsyncSession,
    category_ids: list[int],
) -> dict[int, list[CategoryPrompt]]:
    if not category_ids:
        return {}
    result = await db.execute(
        select(CategoryPrompt)
        .where(CategoryPrompt.category_id.in_(category_ids))
        .options(selectinload(CategoryPrompt.prompt))
    )
    m: dict[int, list[CategoryPrompt]] = {}
    for cp in result.scalars().all():
        m.setdefault(cp.category_id, []).append(cp)
    for prompt_list in m.values():
        prompt_list.sort(key=lambda prompt: prompt.sort_order)
    return m


def _select_scored_categories(
    categories: list[Category],
    requested_locales: list[str],
    total_needed: int,
) -> list[Category]:
    scored_groups: dict[int, list[Category]] = defaultdict(list)
    for category in categories:
        score = len(_locales(category).intersection(requested_locales))
        if score > 0:
            scored_groups[score].append(category)

    selected: list[Category] = []
    for score in sorted(scored_groups, reverse=True):
        group = scored_groups[score]
        random.shuffle(group)
        needed = total_needed - len(selected)
        selected.extend(group[:needed])
        if len(selected) >= total_needed:
            break
    return selected


async def list_locale_availability(
    db: AsyncSession,
    *,
    difficulty: Difficulty | None,
) -> list[LocaleAvailabilityItem]:
    """Return locale availability counts for system categories."""
    cached = await redis.get_cached_category_locale_availability(difficulty)
    if cached is not None:
        return [LocaleAvailabilityItem.model_validate(item) for item in cached]

    query = select(Category).where(Category.source == SYSTEM_CATEGORY_SOURCE)
    if difficulty:
        query = query.where(Category.difficulty == difficulty.lower())

    categories = list((await db.execute(query)).scalars().all())
    totals: dict[str, int] = defaultdict(int)
    per_difficulty: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for category in categories:
        for locale in _locales(category):
            totals[locale] += 1
            per_difficulty[locale][category.difficulty] += 1

    payload = [
        LocaleAvailabilityItem(
            locale=locale,
            category_count=count,
            difficulty_counts=dict(sorted(per_difficulty[locale].items())),
        )
        for locale, count in sorted(totals.items())
    ]

    await redis.cache_category_locale_availability(
        difficulty,
        [item.model_dump() for item in payload],
    )

    return payload


async def select_category_ids(
    db: AsyncSession,
    *,
    difficulty: Difficulty,
    player_count: int,
    locales: list[LanguageCode],
    room_locale: LanguageCode,
) -> list[int]:
    """Pick up to one category per player, preferring those playable in most of the players' locales.

    Falls back to English categories when none suits any of `locales` or `room_locale`.
    """
    requested_locales = _normalize_locale_list(locales, fallback=_normalize_locale(room_locale))

    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.source == SYSTEM_CATEGORY_SOURCE,
    )
    all_categories = list((await db.execute(query)).scalars().all())

    valid_categories = [category for category in all_categories if _locales(category).intersection(requested_locales)]

    if not valid_categories and DEFAULT_LANGUAGE_CODE not in requested_locales:
        requested_locales.append(DEFAULT_LANGUAGE_CODE)
        valid_categories = [category for category in all_categories if DEFAULT_LANGUAGE_CODE in _locales(category)]

    if not valid_categories:
        locale_text = ", ".join(requested_locales)
        raise HTTPException(
            status_code=404,
            detail=f"No categories found for difficulty {difficulty} in locales [{locale_text}]",
        )

    total_needed = min(player_count, len(valid_categories))
    return [category.id for category in _select_scored_categories(valid_categories, requested_locales, total_needed)]


async def deal_category(
    db: AsyncSession,
    *,
    category_id: int,
    preferred_locale: LanguageCode,
    fallback_locale: LanguageCode,
) -> PlayerPromptAssignmentState:
    """Build one player's card from a category.

    The card uses the first locale the category is translated into from: the player's,
    the room's, the category's default, English; failing all, its alphabetically first.
    """
    category = await _get_visible_category_or_404(db, category_id=category_id)
    prompts_by_cat = await _load_category_prompts(db, [category_id])

    candidate_locales = _normalize_locale_list(
        [preferred_locale, fallback_locale, category.default_locale],
        fallback=DEFAULT_LANGUAGE_CODE,
    )
    # A locale listed as playable can still lack its translation until available_locales is recomputed.
    available = {locale for locale in _locales(category) if locale in category.translations}
    chosen_locale = next((loc for loc in candidate_locales if loc in available), None)
    if chosen_locale is None and available:
        chosen_locale = min(available)
    if chosen_locale is None:
        raise HTTPException(status_code=404, detail="Category has no available locales")

    ct = category.translations.get(chosen_locale)
    if ct is None:
        raise HTTPException(status_code=404, detail="Category translation not found")

    item_ids: list[int] = []
    items: list[str] = []
    alternatives: dict[str, list[str]] = {}
    for cp in prompts_by_cat.get(category_id, []):
        pt = cp.prompt.translations.get(chosen_locale)
        if pt is None:
            continue
        item_ids.append(cp.prompt_id)
        label = pt.get("label", "")
        items.append(label)
        alternatives[label] = pt.get("aliases", [])

    return PlayerPromptAssignmentState(
        category_id=category_id,
        category=ct.get("name", ""),
        item_ids=item_ids,
        items=items,
        alternatives=alternatives,
    )


async def get_localized_scoring_targets(
    db: AsyncSession,
    *,
    category_id: int,
    prompt_ids: list[int],
    preferred_locale: LanguageCode,
) -> LocalizedScoringTargets:
    """Resolve prompt ids to localized scoring targets."""
    # Check cache first
    cached = await redis.get_cached_localized_scoring_targets(category_id, preferred_locale, prompt_ids)
    if cached is not None:
        return LocalizedScoringTargets(
            category_id=cached["category_id"],
            category_name=cached["category_name"],
            targets=[GuessTarget(**t) for t in cached["targets"]],
        )

    category = await _get_visible_category_or_404(db, category_id=category_id)

    target_locale = _normalize_locale(preferred_locale)
    if target_locale not in category.translations:
        target_locale = _normalize_locale(category.default_locale)
        if target_locale not in category.translations:
            target_locale = next(iter(category.translations.keys()), None)

    if target_locale is None:
        raise HTTPException(status_code=404, detail="Category translation not found")

    ct = category.translations.get(target_locale)
    if ct is None:
        raise HTTPException(status_code=404, detail="Category translation not found")

    prompts = list((await db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids)))).scalars().all())

    targets: list[GuessTarget] = []
    for p in prompts:
        pt = p.translations.get(target_locale)
        if not pt:
            pt = p.translations.get(_normalize_locale(category.default_locale))
        if not pt and p.translations:
            pt = next(iter(p.translations.values()))

        if pt:
            targets.append(GuessTarget(item_id=p.id, label=pt.get("label", ""), aliases=pt.get("aliases", [])))

    result = LocalizedScoringTargets(category_id=category.id, category_name=ct.get("name", ""), targets=targets)
    await redis.cache_localized_scoring_targets(category_id, preferred_locale, prompt_ids, asdict(result))
    return result
