"""Category catalog and selection logic shared by HTTP routes (M2M + Denormalize Refactor)."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, cast

from fastapi import HTTPException
from sqlalchemy import cast as sa_cast
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload

from app.categories.models import Category, CategoryPrompt, Prompt, normalize_locale_code
from app.categories.schemas import (
    CategoryListItem,
    CategorySelectionResponse,
    LocaleAvailabilityItem,
    SelectedCategorySet,
)
from app.core import redis
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


def _category_available_locales(category: Category) -> set[str]:
    return {normalized for raw in category.available_locales if (normalized := normalize_locale_code(raw)) is not None}


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


def _score_category_by_locales(category: Category, requested_locales: list[str]) -> int:
    available = {loc.lower() for loc in category.available_locales}
    return sum(1 for locale in requested_locales if locale.lower() in available)


def _select_scored_categories(
    categories: list[Category],
    requested_locales: list[str],
    total_needed: int,
) -> list[Category]:
    scored_groups: dict[int, list[Category]] = defaultdict(list)
    for category in categories:
        score = _score_category_by_locales(category, requested_locales)
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


def _select_locale_for_category(category: Category, requested_locales: list[str]) -> str | None:
    category_locales = {loc.lower() for loc in category.available_locales}
    return next((locale for locale in requested_locales if locale.lower() in category_locales), None)


def _category_supports_locale(category: Category, locale: str) -> bool:
    return locale.lower() in {loc.lower() for loc in category.available_locales}


def _build_selected_category_set(
    category: Category,
    selected_locale: str,
    prompts: list[CategoryPrompt],
) -> SelectedCategorySet | None:
    ct = category.translations.get(selected_locale)
    if not ct:
        return None

    item_ids: list[int] = []
    items: list[str] = []
    alternatives: dict[str, list[str]] = {}
    for cp in prompts:
        pt = cp.prompt.translations.get(selected_locale)
        if not pt:
            continue
        item_ids.append(cp.prompt_id)
        label = pt.get("label", "")
        items.append(label)
        alternatives[label] = pt.get("aliases", [])

    return SelectedCategorySet(
        category_id=category.id,
        category_name=ct.get("name", ""),
        item_ids=item_ids,
        items=items,
        alternatives=alternatives,
    )


async def list_categories(
    db: AsyncSession,
    *,
    difficulty: Difficulty | None,
    language: LanguageCode | None,
) -> list[CategoryListItem]:
    """List categories filtered by denormalized available_locales field."""
    requested_locale = _normalize_locale(language)

    # Use Postgres JSONB '@>' operator for fast intersection check
    query = select(Category).where(sa_cast(Category.available_locales, JSONB).contains([requested_locale]))

    if difficulty:
        query = query.where(Category.difficulty == difficulty.lower())

    categories = list((await db.execute(query)).scalars().all())

    payload: list[CategoryListItem] = []
    for c in categories:
        translation = c.translations.get(requested_locale)
        if translation:
            payload.append(
                CategoryListItem(
                    id=c.id,
                    name=translation.get("name", ""),
                    difficulty=cast("Difficulty", c.difficulty),
                    locale=requested_locale,
                )
            )
    return payload


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
        unique_locales = _category_available_locales(category)
        for locale in unique_locales:
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


async def select_category_sets(
    db: AsyncSession,
    *,
    difficulty: Difficulty,
    count: int,
    player_count: int,
    locale: LanguageCode | None,
    locales: list[LanguageCode] | None = None,
) -> CategorySelectionResponse:
    """Select categories using pre-computed available_locales."""
    requested_locales = _normalize_locale_list(locales, fallback=_normalize_locale(locale))

    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.source == SYSTEM_CATEGORY_SOURCE,
    )
    all_categories = list((await db.execute(query)).scalars().all())

    valid_categories = [
        category for category in all_categories if _score_category_by_locales(category, requested_locales) > 0
    ]

    if not valid_categories and DEFAULT_LANGUAGE_CODE not in requested_locales:
        requested_locales.append(DEFAULT_LANGUAGE_CODE)
        valid_categories = [
            category for category in all_categories if _category_supports_locale(category, DEFAULT_LANGUAGE_CODE)
        ]

    if not valid_categories:
        locale_text = ", ".join(requested_locales)
        raise HTTPException(
            status_code=404,
            detail=f"No categories found for difficulty {difficulty} in locales [{locale_text}]",
        )

    total_needed = min(count * player_count, len(valid_categories))
    selected = _select_scored_categories(valid_categories, requested_locales, total_needed)

    prompts_by_cat = await _load_category_prompts(db, [c.id for c in selected])

    selections: list[SelectedCategorySet] = []
    for c in selected:
        selected_locale = _select_locale_for_category(c, requested_locales)
        if selected_locale is None:
            continue

        selection = _build_selected_category_set(c, selected_locale, prompts_by_cat.get(c.id, []))
        if selection is not None:
            selections.append(selection)

    return CategorySelectionResponse(difficulty=difficulty, selections=selections)


async def get_localized_category_set(
    db: AsyncSession,
    *,
    category_id: int,
    preferred_locale: LanguageCode,
    fallback_locale: LanguageCode,
) -> SelectedCategorySet:
    """Resolve a category into one internally consistent locale for room gameplay."""
    category = await _get_visible_category_or_404(db, category_id=category_id)
    prompts_by_cat = await _load_category_prompts(db, [category_id])

    candidate_locales = _normalize_locale_list(
        [preferred_locale, fallback_locale, category.default_locale],
        fallback=DEFAULT_LANGUAGE_CODE,
    )
    available_set = {loc.lower() for loc in category.available_locales}
    chosen_locale = next((loc for loc in candidate_locales if loc.lower() in available_set), None)
    if chosen_locale is None and category.available_locales:
        chosen_locale = sorted(category.available_locales)[0]
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

    return SelectedCategorySet(
        category_id=category_id,
        category_name=ct.get("name", ""),
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
    cached = await redis.get_cached_localized_scoring_targets(category_id, preferred_locale)
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
    await redis.cache_localized_scoring_targets(category_id, preferred_locale, asdict(result))
    return result
