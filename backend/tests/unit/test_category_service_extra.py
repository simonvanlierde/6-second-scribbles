"""Additional category service coverage for locale fallback and caching branches."""
# spell-checker: ignore animaux, animales, gato, minou

from __future__ import annotations

from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.categories.models import Category, CategoryPrompt, Prompt
from app.categories.service import (
    _normalize_locale_list,
    _select_scored_categories,
    deal_category,
    get_localized_scoring_targets,
    select_category_ids,
)
from app.core import redis as redis_module

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.ext.asyncio import AsyncSession

ANIMAUX = "Animaux"
ANIMALES = "Animales"
ANIMALS = "Animals"
CAT = "cat"
GATO = "gato"
SWEDISH_IN_SPANISH_ROOM = "sv>es"
ZH_TW_ANIMALS = "動物"
ZH_TW_CAT = "貓"


class _ScalarResult:
    def __init__(self, items: Sequence[object]) -> None:
        self._items = list(items)

    def all(self) -> list[object]:
        return list(self._items)


class _ExecuteResult:
    def __init__(self, items: Sequence[object]) -> None:
        self._items = list(items)

    def scalar_one_or_none(self) -> object | None:
        return self._items[0] if self._items else None

    def scalars(self) -> _ScalarResult:
        return _ScalarResult(self._items)


class _QueuedSession:
    def __init__(self, *results: Sequence[object]) -> None:
        self._results = list(results)

    async def execute(self, _statement: object) -> _ExecuteResult:
        return _ExecuteResult(self._results.pop(0))


def _category(*, category_id: int, available_locales: list[str], translations: dict[str, object]) -> Category:
    return Category(
        id=category_id,
        difficulty="easy",
        default_locale="en",
        source="system",
        available_locales=available_locales,
        translations=translations,
    )


def _category_prompt(
    *,
    category_id: int,
    prompt_id: int,
    translations: dict[str, object],
    sort_order: int = 0,
) -> CategoryPrompt:
    prompt = Prompt(id=prompt_id, stable_key=f"prompt-{prompt_id}", translations=translations)
    return CategoryPrompt(category_id=category_id, prompt_id=prompt_id, sort_order=sort_order, prompt=prompt)


def test_normalize_locale_list_deduplicates_and_appends_fallback() -> None:
    """Locale lists are normalized once and always include the fallback."""
    assert _normalize_locale_list(["FR-ca", "fr", "nl_NL"], fallback="en") == ["fr-CA", "fr", "nl-NL", "en"]


def test_select_scored_categories_prefers_higher_locale_scores(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selection keeps the highest-scoring categories first."""
    categories = [
        _category(category_id=1, available_locales=["en"], translations={"en": {"name": "Only English"}}),
        _category(
            category_id=2,
            available_locales=["en", "fr"],
            translations={"en": {"name": "Bilingual"}},
        ),
    ]
    monkeypatch.setattr("app.categories.service.random.shuffle", lambda _items: None)

    selected = _select_scored_categories(categories, ["fr", "en"], total_needed=1)

    assert [category.id for category in selected] == [2]


async def test_deal_category_skips_missing_prompt_translation() -> None:
    """Prompt entries without the chosen locale are skipped."""
    category = _category(category_id=7, available_locales=["fr"], translations={"fr": {"name": "Animaux"}})
    prompts = [
        _category_prompt(category_id=7, prompt_id=11, translations={"fr": {"label": "chat", "aliases": ["minou"]}}),
        _category_prompt(category_id=7, prompt_id=12, translations={"en": {"label": "dog", "aliases": []}}),
    ]
    session = _QueuedSession([category], prompts)

    card = await deal_category(
        cast("AsyncSession", session), category_id=7, preferred_locale="fr", fallback_locale="fr"
    )

    assert card.category == ANIMAUX
    assert card.item_ids == [11]
    assert card.items == ["chat"]
    assert card.alternatives == {"chat": ["minou"]}


async def test_select_falls_back_to_english(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selection falls back to English when the requested locale has no matches."""
    category = _category(
        category_id=1,
        available_locales=["en"],
        translations={"en": {"name": "Animals"}},
    )
    prompts = [_category_prompt(category_id=1, prompt_id=10, translations={"en": {"label": "cat", "aliases": []}})]
    session = _QueuedSession([category], [category], prompts)

    monkeypatch.setattr("app.categories.service.random.shuffle", lambda _items: None)

    category_ids = await select_category_ids(
        cast("AsyncSession", session), difficulty="easy", player_count=1, locales=["fr"], room_locale="fr"
    )
    card = await deal_category(
        cast("AsyncSession", session), category_id=1, preferred_locale="fr", fallback_locale="fr"
    )

    assert category_ids == [1]
    assert card.category == ANIMALS
    assert card.items == [CAT]


async def test_select_and_deal_keep_region_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Selection and prompt resolution preserve region-specific content locales."""
    category = _category(
        category_id=2,
        available_locales=["zh-CN", "zh-TW"],
        translations={"zh-CN": {"name": "动物"}, "zh-TW": {"name": "動物"}},
    )
    prompts = [
        _category_prompt(
            category_id=2,
            prompt_id=20,
            translations={
                "zh-CN": {"label": "猫", "aliases": []},
                "zh-TW": {"label": "貓", "aliases": []},
            },
        )
    ]
    session = _QueuedSession([category], [category], prompts)

    monkeypatch.setattr("app.categories.service.random.shuffle", lambda _items: None)

    category_ids = await select_category_ids(
        cast("AsyncSession", session), difficulty="easy", player_count=1, locales=["zh-TW"], room_locale="zh-TW"
    )
    card = await deal_category(
        cast("AsyncSession", session), category_id=2, preferred_locale="zh-TW", fallback_locale="zh-TW"
    )

    assert category_ids == [2]
    assert card.category == ZH_TW_ANIMALS
    assert card.items == [ZH_TW_CAT]


async def test_deal_category_raises_when_no_available_locales() -> None:
    """Categories with no available locales return a 404."""
    session = _QueuedSession(
        [_category(category_id=4, available_locales=[], translations={"en": {"name": "Animals"}})],
        [],
    )

    with pytest.raises(HTTPException, match="Category has no available locales"):
        await deal_category(
            cast("AsyncSession", session),
            category_id=4,
            preferred_locale="fr",
            fallback_locale="nl",
        )


async def test_deal_category_uses_first_available_locale_when_preferences_miss() -> None:
    """When no preferred locale matches, the first available locale is used."""
    category = _category(
        category_id=9,
        available_locales=["es", "fr"],
        translations={"es": {"name": "Animales"}, "fr": {"name": "Animaux"}},
    )
    prompts = [_category_prompt(category_id=9, prompt_id=90, translations={"es": {"label": "gato", "aliases": []}})]
    session = _QueuedSession([category], prompts)

    selection = await deal_category(
        cast("AsyncSession", session),
        category_id=9,
        preferred_locale="de",
        fallback_locale="it",
    )

    assert selection.category == ANIMALES
    assert selection.items == [GATO]


async def test_get_localized_scoring_targets_uses_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cached localized targets bypass the database."""
    monkeypatch.setattr(
        redis_module,
        "get_cached_localized_scoring_targets",
        AsyncMock(
            return_value={
                "category_id": 3,
                "category_name": "Animals",
                "locale": "en",
                "targets": [{"item_id": 30, "label": "cat", "aliases": ["kitty"]}],
            }
        ),
    )

    result = await get_localized_scoring_targets(
        cast("AsyncSession", _QueuedSession()),
        category_id=3,
        prompt_ids=[30],
        preferred_locale="en",
        fallback_locale="en",
    )

    assert result.category_name == ANIMALS
    assert result.targets[0].label == CAT


async def test_get_localized_scoring_targets_falls_back_to_default_and_caches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prompt targets fall back through category-default locale and then cache the result."""
    cache_write = AsyncMock()
    monkeypatch.setattr(redis_module, "get_cached_localized_scoring_targets", AsyncMock(return_value=None))
    monkeypatch.setattr(redis_module, "cache_localized_scoring_targets", cache_write)

    category = _category(
        category_id=5,
        available_locales=["en"],
        translations={"en": {"name": "Animals"}},
    )
    prompt = Prompt(
        id=50,
        stable_key="cat",
        translations={"en": {"label": "cat", "aliases": ["kitty"]}},
    )
    session = _QueuedSession([category], [prompt])

    result = await get_localized_scoring_targets(
        cast("AsyncSession", session),
        category_id=5,
        prompt_ids=[50],
        preferred_locale="fr",
        fallback_locale="fr",
    )

    assert result.category_name == ANIMALS
    assert result.targets[0].aliases == ["kitty"]
    cache_write.assert_awaited_once()


async def test_scoring_uses_the_room_language_like_the_card(monkeypatch: pytest.MonkeyPatch) -> None:
    """A guesser whose language the category lacks is scored in the room's language, as their card is dealt."""
    monkeypatch.setattr(redis_module, "get_cached_localized_scoring_targets", AsyncMock(return_value=None))
    cache_write = AsyncMock()
    monkeypatch.setattr(redis_module, "cache_localized_scoring_targets", cache_write)
    category = _category(
        category_id=7, available_locales=["en", "es"], translations={"en": {"name": ANIMALS}, "es": {"name": ANIMALES}}
    )
    prompt = Prompt(
        id=70,
        stable_key="cat",
        translations={"en": {"label": CAT, "aliases": []}, "es": {"label": GATO, "aliases": []}},
    )
    session = _QueuedSession([category], [prompt])

    result = await get_localized_scoring_targets(
        cast("AsyncSession", session),
        category_id=7,
        prompt_ids=[70],
        preferred_locale="sv",
        fallback_locale="es",
    )

    assert result.category_name == ANIMALES
    assert [target.label for target in result.targets] == [GATO]
    # Another room language picks other targets, so it must not share the cache entry.
    assert cache_write.await_args_list[0].args[1] == SWEDISH_IN_SPANISH_ROOM


async def test_untranslated_room_language_is_dealt_in_a_fallback_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    """A category listed for the room's language but missing that translation is still dealt."""
    category = _category(category_id=5, available_locales=["nl", "en"], translations={"en": {"name": ANIMALS}})
    prompts = [_category_prompt(category_id=5, prompt_id=50, translations={"en": {"label": CAT, "aliases": []}})]
    session = _QueuedSession([category], [category], prompts)
    monkeypatch.setattr("app.categories.service.random.shuffle", lambda _items: None)

    category_ids = await select_category_ids(
        cast("AsyncSession", session), difficulty="easy", player_count=1, locales=["nl"], room_locale="nl"
    )
    card = await deal_category(
        cast("AsyncSession", session), category_id=5, preferred_locale="nl", fallback_locale="nl"
    )

    assert category_ids == [5]
    assert card.category == ANIMALS
    assert card.items == [CAT]
