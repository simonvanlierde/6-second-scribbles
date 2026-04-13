"""Category catalog and selection logic shared by HTTP routes (M2M + Denormalize Refactor)."""

from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING
from typing import cast as type_cast

from fastapi import HTTPException
from sqlalchemy import cast as sql_cast
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB

from app.categories.models import Category, CategoryPrompt, Prompt, normalize_locale_code
from app.categories.schemas import (
    CategoryListItem,
    CategorySelectionResponse,
    GuessScoreRequest,
    GuessScoreResponse,
    LocaleAvailabilityItem,
    SelectedCategorySet,
)
from app.core import redis
from app.scoring import guess_matcher
from app.scoring.services import GuessTarget

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.core.types import Difficulty, LanguageCode


@dataclass(frozen=True)
class LocalizedScoringTargets:
    """Localized scoring targets for one assigned category prompt."""

    category_id: int
    category_name: str
    targets: list[GuessTarget]


@dataclass(frozen=True)
class LocalizedCategorySet:
    """Localized category payload used by room assignment flow."""

    category_id: int
    category_name: str
    item_ids: list[int]
    items: list[str]
    alternatives: dict[str, list[str]]


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
        select(CategoryPrompt).where(CategoryPrompt.category_id.in_(category_ids)).join(CategoryPrompt.prompt)
    )
    m: dict[int, list[CategoryPrompt]] = {}
    for cp in result.scalars().all():
        m.setdefault(cp.category_id, []).append(cp)
    for prompt_list in m.values():
        prompt_list.sort(key=lambda prompt: prompt.sort_order)
    return m


async def list_categories(
    db: AsyncSession,
    *,
    difficulty: Difficulty | None,
    language: LanguageCode | None,
) -> list[CategoryListItem]:
    """List categories filtered by denormalized available_locales field."""
    requested_locale = _normalize_locale(language)

    # Use Postgres JSONB '@>' operator for fast intersection check
    query = select(Category).where(sql_cast(Category.available_locales, JSONB).contains([requested_locale]))

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
                    difficulty=type_cast("Difficulty", c.difficulty),
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
    room_id: str | None = None,
    difficulty: Difficulty,
    count: int,
    player_count: int,
    locale: LanguageCode | None,
    locales: list[LanguageCode] | None = None,
    owner_user_id: str | None = None,
    enabled_custom_category_ids: list[int] | None = None,
) -> CategorySelectionResponse:
    """Select categories using pre-computed available_locales."""
    _ = (room_id, owner_user_id, enabled_custom_category_ids)
    requested_locales = _normalize_locale_list(locales, fallback=_normalize_locale(locale))

    query = select(Category).where(
        Category.difficulty == difficulty.lower(),
        Category.source == SYSTEM_CATEGORY_SOURCE,
    )
    all_categories = list((await db.execute(query)).scalars().all())

    # Score categories by how many requested locales they satisfy
    valid_categories = []
    for category in all_categories:
        avail = {loc.lower() for loc in category.available_locales}
        score = sum(1 for loc in requested_locales if loc in avail)
        if score > 0:
            valid_categories.append((category, score))

    if not valid_categories and DEFAULT_LANGUAGE_CODE not in requested_locales:
        requested_locales.append(DEFAULT_LANGUAGE_CODE)
        for category in all_categories:
            avail = {loc.lower() for loc in category.available_locales}
            if DEFAULT_LANGUAGE_CODE in avail:
                valid_categories.append((category, 1))

    if not valid_categories:
        locale_text = ", ".join(requested_locales)
        raise HTTPException(
            status_code=404,
            detail=f"No categories found for difficulty {difficulty} in locales [{locale_text}]",
        )

    scored_groups = defaultdict(list)
    for cat, score in valid_categories:
        scored_groups[score].append(cat)

    total_needed = min(count * player_count, len(valid_categories))
    selected = []
    for score in sorted(scored_groups.keys(), reverse=True):
        group = scored_groups[score]
        random.shuffle(group)
        needed = total_needed - len(selected)
        if len(group) <= needed:
            selected.extend(group)
        else:
            selected.extend(group[:needed])
        if len(selected) == total_needed:
            break

    prompts_by_cat = await _load_category_prompts(db, [c.id for c in selected])

    selections: list[SelectedCategorySet] = []
    for c in selected:
        category_locales = {loc.lower() for loc in c.available_locales}
        selected_locale = next((loc for loc in requested_locales if loc in category_locales), None)
        if selected_locale is None:
            continue

        ct = c.translations.get(selected_locale)
        if not ct:
            continue

        items, item_ids, alts = [], [], {}
        for cp in prompts_by_cat.get(c.id, []):
            pt = cp.prompt.translations.get(selected_locale)
            if not pt:
                continue
            item_ids.append(cp.prompt_id)
            label = pt.get("label", "")
            items.append(label)
            alts[label] = pt.get("aliases", [])

        selections.append(
            SelectedCategorySet(
                category_id=c.id, category_name=ct.get("name", ""), item_ids=item_ids, items=items, alternatives=alts
            )
        )

    return CategorySelectionResponse(difficulty=difficulty, selections=selections)


async def get_localized_category_set(
    db: AsyncSession,
    *,
    category_id: int,
    preferred_locale: LanguageCode,
    fallback_locale: LanguageCode,
) -> LocalizedCategorySet:
    """Resolve a category into one internally consistent locale for room gameplay."""
    category = await _get_visible_category_or_404(db, category_id=category_id)
    prompts_by_cat = await _load_category_prompts(db, [category_id])

    candidate_locales = _normalize_locale_list(
        [preferred_locale, fallback_locale, category.default_locale],
        fallback=DEFAULT_LANGUAGE_CODE,
    )
    available_set = {loc.lower() for loc in category.available_locales}
    chosen_locale = next((loc for loc in candidate_locales if loc in available_set), None)
    if chosen_locale is None and category.available_locales:
        chosen_locale = sorted(loc.lower() for loc in category.available_locales)[0]
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

    return LocalizedCategorySet(
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

    target_locale = preferred_locale.lower()
    if target_locale not in category.translations:
        target_locale = category.default_locale.lower()
        if target_locale not in category.translations:
            target_locale = next(iter(category.translations.keys()), None)

    if target_locale is None:
        raise HTTPException(status_code=404, detail="Category translation not found")

    ct = category.translations.get(target_locale)

    prompts = list((await db.execute(select(Prompt).where(Prompt.id.in_(prompt_ids)))).scalars().all())

    targets: list[GuessTarget] = []
    for p in prompts:
        pt = p.translations.get(target_locale)
        if not pt:
            pt = p.translations.get(category.default_locale.lower())
        if not pt and p.translations:
            pt = next(iter(p.translations.values()))

        if pt:
            targets.append(GuessTarget(item_id=p.id, label=pt.get("label", ""), aliases=pt.get("aliases", [])))

    result = LocalizedScoringTargets(category_id=category.id, category_name=ct.get("name", ""), targets=targets)
    await redis.cache_localized_scoring_targets(category_id, preferred_locale, asdict(result))
    return result


def score_guess_request(request: GuessScoreRequest) -> GuessScoreResponse:
    """Score player guesses against accepted answers and aliases."""
    res = guess_matcher.score_guesses(
        guesses=request.guesses, correct_answers=request.correct_answers, alternatives_map=request.alternatives
    )
    return GuessScoreResponse(
        score=res.score,
        total=res.total,
        percentage=res.percentage,
        matches=res.matches,
        unmatched_answers=res.unmatched_answers,
    )
