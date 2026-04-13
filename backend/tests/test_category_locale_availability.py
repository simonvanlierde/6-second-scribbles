"""Focused tests for locale availability normalization and caching."""
# spell-checker: ignore setex

from __future__ import annotations

from typing import Any, cast

from app.categories.models import Category
from app.categories.service import list_locale_availability
from app.core import redis as redis_module


class _ScalarResult:
    def __init__(self, items):
        self._items = items

    def all(self):
        return list(self._items)


class _ExecuteResult:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return _ScalarResult(self._items)


class _FakeSession:
    def __init__(self, categories):
        self._categories = categories

    async def execute(self, _statement):
        return _ExecuteResult(self._categories)


class _FakeRedis:
    def __init__(self):
        self.store: dict[str, str] = {}

    async def setex(self, key: str, _ttl: int, value: str):
        self.store[key] = value

    async def get(self, key: str):
        return self.store.get(key)


async def test_list_locale_availability_uses_cached_payload(monkeypatch):
    async def _cached(_difficulty):
        return [
            {"locale": "en", "category_count": 4, "difficulty_counts": {"easy": 2, "hard": 2}},
        ]

    async def _cache_write(_difficulty, _items):
        raise AssertionError

    monkeypatch.setattr(redis_module, "get_cached_category_locale_availability", _cached)
    monkeypatch.setattr(redis_module, "cache_category_locale_availability", _cache_write)

    result = await list_locale_availability(cast("Any", _FakeSession([])), difficulty=None)

    assert len(result) == 1
    assert result[0].locale == "en"
    assert result[0].category_count == 4


async def test_list_locale_availability_normalizes_locales_and_caches(monkeypatch):
    written: list[tuple[str | None, list[dict]]] = []

    async def _no_cache(_difficulty):
        return None

    async def _cache_write(difficulty, items):
        written.append((difficulty, items))

    monkeypatch.setattr(redis_module, "get_cached_category_locale_availability", _no_cache)
    monkeypatch.setattr(redis_module, "cache_category_locale_availability", _cache_write)

    categories = [
        Category(difficulty="easy", default_locale="en", source="system", available_locales=["en", "fr-CA"]),
        Category(difficulty="hard", default_locale="en", source="system", available_locales=["fr", "es-MX", "@@"]),
    ]

    result = await list_locale_availability(cast("Any", _FakeSession(categories)), difficulty=None)

    as_map = {item.locale: item for item in result}
    assert as_map["en"].category_count == 1
    assert as_map["es"].category_count == 1
    assert as_map["fr"].category_count == 2
    assert as_map["fr"].difficulty_counts == {"easy": 1, "hard": 1}

    assert len(written) == 1
    assert written[0][0] is None
    cached_locales = {item["locale"] for item in written[0][1]}
    assert cached_locales == {"en", "es", "fr"}


async def test_redis_locale_availability_cache_roundtrip(monkeypatch):
    fake_redis = _FakeRedis()

    async def _get_redis():
        return fake_redis

    monkeypatch.setattr(redis_module, "get_redis", _get_redis)

    await redis_module.cache_category_locale_availability(
        "easy",
        [{"locale": "en", "category_count": 3, "difficulty_counts": {"easy": 3}}],
    )

    cached = await redis_module.get_cached_category_locale_availability("easy")

    assert cached is not None
    assert cached[0]["locale"] == "en"
    assert cached[0]["category_count"] == 3
