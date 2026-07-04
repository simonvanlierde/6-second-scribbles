"""Focused coverage for Redis helpers and translation infrastructure."""
# spell-checker: ignore chien, gato, setex

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from redis.exceptions import RedisError

from app.core import redis as redis_module
from app.rooms.state import RoomState
from scripts import auto_translate_seed_data as auto_translate
from translation.argos_provider import ArgosTranslationProvider
from translation.cache import CacheStats, PersistentTranslationCache
from translation.service import TranslationService

AUTO_TRANSLATE_MODULE = auto_translate
ROOM_SCAN_PATTERN = "room:*"
ROOM_KEY_PREFIX = "room:"
ROOM_ID = "ROOM01"
USER_ID = "user-1"
TRANSLATED_CHAT = "chat"
TRANSLATED_DOG = "chien"
TRANSLATED_CAT_ES = "gato"
ZERO_RATE_SUMMARY = "Cache hit rate: 0.0% (0/0 hits) | writes: 0"
SUMMARY_HALF_HIT = "50.0%"
PROMPTS_LINE = "prompts: []"
SAME_TEXT = "same"


class _FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    async def setex(self, key: str, ttl: int, value: str) -> None:
        self.store[key] = value
        self.expirations[key] = ttl

    async def get(self, key: str) -> str | None:
        return self.store.get(key)

    async def delete(self, key: str) -> None:
        self.store.pop(key, None)

    async def scan_iter(self, *, match: str) -> object:
        for key in list(self.store):
            if match == ROOM_SCAN_PATTERN and key.startswith(ROOM_KEY_PREFIX):
                yield key

    async def mget(self, keys: list[str]) -> list[str | None]:
        return [self.store.get(key) for key in keys]

    async def incr(self, key: str) -> int:
        next_value = int(self.store.get(key, "0")) + 1
        self.store[key] = str(next_value)
        return next_value

    async def expire(self, key: str, ttl: int) -> None:
        self.expirations[key] = ttl

    async def ttl(self, key: str) -> int:
        return self.expirations.get(key, -1)


class _MemoryCache:
    def __init__(self) -> None:
        self.values: dict[tuple[str, str, str], str] = {}
        self.reset_called = False
        self.summary = "Cache hit rate: 0.0% (0/0 hits) | writes: 0"

    def get(self, from_locale: str, to_locale: str, text: str) -> str | None:
        return self.values.get((from_locale, to_locale, text))

    def put(self, from_locale: str, to_locale: str, text: str, translation: str) -> None:
        self.values[(from_locale, to_locale, text)] = translation

    def reset(self) -> None:
        self.values.clear()
        self.reset_called = True

    def stats_summary(self) -> str:
        return self.summary


class _ProviderHarness(ArgosTranslationProvider):
    def ensure_pair(self, from_locale: str, to_locale: str) -> None:
        self._ensure_pair(from_locale, to_locale)


class _FakeProvider:
    def __init__(self) -> None:
        self.translate = Mock(return_value=TRANSLATED_CHAT)
        self.prefetch_pairs = Mock()


def _make_provider() -> _ProviderHarness:
    provider = _ProviderHarness.__new__(_ProviderHarness)
    provider.installed_pairs = set()
    provider.available_packages = []
    provider.argos_package = SimpleNamespace(install_from_path=Mock())
    provider.argos_translate = SimpleNamespace(get_translation_from_codes=Mock())
    return provider


async def test_room_state_and_session_round_trip(monkeypatch: pytest.MonkeyPatch) -> None:
    """Room state, sessions, and deletion all round-trip through Redis helpers."""
    fake_redis = _FakeRedis()
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(return_value=fake_redis))
    monkeypatch.setattr(redis_module.secrets, "token_urlsafe", lambda _n: "session-token")

    state = RoomState(room_id=ROOM_ID)
    await redis_module.save_room_state(ROOM_ID, state)
    loaded = await redis_module.load_room_state(ROOM_ID)

    session_id = await redis_module.create_session(USER_ID)
    session_user = await redis_module.get_session_user_id(session_id)
    await redis_module.delete_session(session_id)
    deleted_user = await redis_module.get_session_user_id(session_id)

    assert loaded is not None
    assert loaded.room_id == ROOM_ID
    assert session_user == USER_ID
    assert deleted_user is None


async def test_load_all_room_states_and_rate_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Loading all rooms and fixed-window rate limiting use the expected Redis keys."""
    fake_redis = _FakeRedis()
    fake_redis.store["room:ROOM01"] = RoomState(room_id="ROOM01").model_dump_json()
    fake_redis.store["room:ROOM02"] = RoomState(room_id="ROOM02").model_dump_json()
    monkeypatch.setattr(redis_module, "get_redis", AsyncMock(return_value=fake_redis))

    states = await redis_module.load_all_room_states()
    first_count, retry_after = await redis_module.increment_rate_limit("auth_guest", "127.0.0.1", window_seconds=30)

    assert sorted(state.room_id for state in states) == ["ROOM01", "ROOM02"]
    assert first_count == 1
    assert retry_after == 30


async def test_redis_helpers_fall_back_cleanly_on_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Error paths log and return safe defaults."""
    failing = AsyncMock(side_effect=RedisError("boom"))
    monkeypatch.setattr(redis_module, "get_redis", failing)

    assert await redis_module.load_room_state("ROOM01") is None
    assert await redis_module.load_all_room_states() == []
    assert await redis_module.get_session_user_id("session-1") is None
    # Rate limiting fails CLOSED: an un-countable request is reported as over-limit
    # so a Redis outage cannot silently disable every throttle.
    count, retry_after = await redis_module.increment_rate_limit("auth", "id", window_seconds=10)
    assert count == sys.maxsize
    assert retry_after == 10
    assert await redis_module.get_cached_localized_scoring_targets(1, "en", [1]) is None
    assert await redis_module.get_cached_category_locale_availability(None) is None


def test_translation_cache_load_put_reset_and_summary(tmp_path: Path) -> None:
    """Persistent translation cache handles save/load/reset and tracks stats."""
    cache_path = tmp_path / "cache.json"
    cache = PersistentTranslationCache(cache_path)

    assert cache.get("en", "fr", "cat") is None
    cache.put("en", "fr", "cat", TRANSLATED_CHAT)
    assert cache.get("en", "fr", "cat") == TRANSLATED_CHAT
    assert SUMMARY_HALF_HIT in cache.stats_summary()

    reloaded = PersistentTranslationCache(cache_path)
    assert reloaded.get("en", "fr", "cat") == TRANSLATED_CHAT

    reloaded.reset()
    assert reloaded.cache == {}
    assert not cache_path.exists()


def test_translation_cache_handles_invalid_json_and_save_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Corrupt cache files and save failures do not crash the cache layer."""
    cache_path = tmp_path / "cache.json"
    cache_path.write_text("{not-json}", encoding="utf-8")

    cache = PersistentTranslationCache(cache_path)
    assert cache.cache == {}

    original_write_text = Path.write_text

    def fail_for_cache(self: Path, data: str, encoding: str | None = None) -> int:
        if self == cache_path:
            message = "disk full"
            raise OSError(message)
        return original_write_text(self, data, encoding=encoding)

    monkeypatch.setattr(Path, "write_text", fail_for_cache)
    cache.put("en", "es", "cat", TRANSLATED_CAT_ES)
    assert cache.cache["en"]["en→es|cat"] == TRANSLATED_CAT_ES


def test_cache_stats_summary_handles_zero_hits() -> None:
    """Empty stats report a zero hit rate."""
    assert CacheStats().format_summary() == ZERO_RATE_SUMMARY


def test_translation_service_uses_persistent_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    """Service checks the persistent cache before calling the provider."""
    provider = _FakeProvider()
    cache = _MemoryCache()
    cache.values[("en", "fr", "dog")] = TRANSLATED_DOG

    monkeypatch.setattr("translation.service.PersistentTranslationCache", lambda _path=None: cache)
    service = TranslationService(provider_class=_FakeProvider)

    assert service.translate("en", "fr", "dog") == TRANSLATED_DOG
    assert service.translate("en", "fr", "dog") == TRANSLATED_DOG
    assert service.translate("en", "fr", "cat") == TRANSLATED_CHAT
    assert service.translate("en", "en", SAME_TEXT) == SAME_TEXT

    provider.translate.assert_not_called()
    assert isinstance(service.provider, _FakeProvider)
    service.provider.translate.assert_called_once_with("en", "fr", "cat")
    service.prefetch_pairs("en", ["fr", "es"])
    service.provider.prefetch_pairs.assert_called_once_with("en", ["fr", "es"])
    assert service.cache_stats() == cache.summary
    service.reset_cache()
    assert cache.reset_called


def test_argos_provider_translate_and_prefetch_paths() -> None:
    """Argos provider trims translations, reuses installed pairs, and prefetches."""
    provider = _make_provider()
    translation = SimpleNamespace(translate=Mock(return_value=" gato "))
    cast("Mock", provider.argos_translate.get_translation_from_codes).return_value = translation

    assert provider.translate("en", "es", "cat") == TRANSLATED_CAT_ES
    provider.prefetch_pairs("en", ["es", "fr"])

    assert ("en", "es") in provider.installed_pairs
    assert ("en", "fr") in provider.installed_pairs


def test_argos_provider_errors_for_missing_dependency_and_package(monkeypatch: pytest.MonkeyPatch) -> None:
    """Provider raises clear runtime errors for missing modules or packages."""
    import_error = Mock(side_effect=ImportError("missing"))
    monkeypatch.setattr("translation.argos_provider.importlib.import_module", import_error)

    with pytest.raises(RuntimeError, match="Argos Translate is not installed"):
        ArgosTranslationProvider()

    provider = _make_provider()
    cast("Mock", provider.argos_translate.get_translation_from_codes).side_effect = AttributeError("missing")

    with pytest.raises(RuntimeError, match="No Argos package available"):
        provider.ensure_pair("en", "it")


def test_auto_translate_helpers_cover_locale_and_cache_commands() -> None:
    """Helper functions normalize locales, dedupe aliases, and handle cache commands."""
    service = SimpleNamespace(
        cache=SimpleNamespace(cache={"en": {"en→fr|cat": "chat"}}, reset=Mock()),
        cache_stats=Mock(return_value="stats"),
    )
    assert AUTO_TRANSLATE_MODULE._normalize_locales([" FR ", "fr", "es"]) == ["fr", "es"]  # noqa: SLF001
    assert AUTO_TRANSLATE_MODULE._normalize_locales(None) == ["es", "fr"]  # noqa: SLF001
    assert AUTO_TRANSLATE_MODULE._dedupe_translated_aliases([" Café ", "cafe", "Chat"]) == ["café", "chat"]  # noqa: SLF001

    assert AUTO_TRANSLATE_MODULE._handle_cache_commands(  # noqa: SLF001
        argparse.Namespace(reset_cache=True, show_cache_stats=False),
        cast("TranslationService", service),
    )
    assert service.cache.reset.called

    assert AUTO_TRANSLATE_MODULE._handle_cache_commands(  # noqa: SLF001
        argparse.Namespace(reset_cache=False, show_cache_stats=True),
        cast("TranslationService", service),
    )
    assert (
        AUTO_TRANSLATE_MODULE._handle_cache_commands(  # noqa: SLF001
            argparse.Namespace(reset_cache=False, show_cache_stats=False),
            cast("TranslationService", service),
        )
        is False
    )


def test_auto_translate_parse_args_and_hash_helpers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Argument parsing and hash helpers stay deterministic."""
    seed_file = tmp_path / "seed.yaml"
    seed_file.write_text("prompts: []\n", encoding="utf-8")
    hash_marker = tmp_path / ".seed_translation_hash"
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "SEED_HASH_FILE", hash_marker)
    monkeypatch.setattr(
        "sys.argv",
        [
            "auto_translate_seed_data.py",
            "--seed-file",
            str(seed_file),
            "--target-locales",
            "it,nl",
            "--dry-run",
        ],
    )

    args = AUTO_TRANSLATE_MODULE.parse_args()
    file_hash = AUTO_TRANSLATE_MODULE._compute_file_hash(seed_file)  # noqa: SLF001
    AUTO_TRANSLATE_MODULE._write_hash(file_hash)  # noqa: SLF001

    assert args.seed_file == seed_file
    assert args.target_locales == ["it", "nl"]
    assert args.dry_run is True
    assert AUTO_TRANSLATE_MODULE._read_last_hash() == file_hash  # noqa: SLF001


def test_auto_translate_main_handles_missing_file_and_runs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI reports missing files and translates a changed seed file."""
    missing_args = argparse.Namespace(
        seed_file=tmp_path / "missing.yaml",
        source_locale="en",
        target_locales=["fr"],
        overwrite_existing=False,
        dry_run=False,
        force=False,
        reset_cache=False,
        show_cache_stats=False,
    )
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "parse_args", lambda: missing_args)

    with pytest.raises(FileNotFoundError, match="Seed file not found"):
        AUTO_TRANSLATE_MODULE.main()

    seed_file = tmp_path / "seed.yaml"
    seed_file.write_text("prompts:\n  - id: cat\nsystem_categories: []\n", encoding="utf-8")
    run_args = argparse.Namespace(
        seed_file=seed_file,
        source_locale="en",
        target_locales=["fr"],
        overwrite_existing=False,
        dry_run=False,
        force=True,
        reset_cache=False,
        show_cache_stats=False,
    )
    service = SimpleNamespace(cache=SimpleNamespace(reset=Mock()), cache_stats=Mock(return_value="stats"))
    apply_auto = Mock(
        return_value={
            "prompts_translated": 0,
            "categories_translated": 0,
            "aliases_translated": 0,
            "total_operations": 0,
            "skipped_missing_source": 0,
        }
    )
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "parse_args", lambda: run_args)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "TranslationService", lambda: service)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "apply_auto_translations", apply_auto)

    AUTO_TRANSLATE_MODULE.main()

    apply_auto.assert_called_once()


def test_auto_translate_main_skips_on_unchanged_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI exits early when the seed file hash has not changed."""
    seed_file = tmp_path / "seed.yaml"
    seed_file.write_text("prompts: []\n", encoding="utf-8")
    service = SimpleNamespace(cache=SimpleNamespace(reset=Mock()), cache_stats=Mock(return_value="stats"))
    args = argparse.Namespace(
        seed_file=seed_file,
        source_locale="en",
        target_locales=["fr"],
        overwrite_existing=False,
        dry_run=False,
        force=False,
        reset_cache=False,
        show_cache_stats=False,
    )

    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "parse_args", lambda: args)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "TranslationService", lambda: service)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "_compute_file_hash", lambda _path: "abc123")
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "_read_last_hash", lambda: "abc123")
    apply_auto = Mock()
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "apply_auto_translations", apply_auto)

    AUTO_TRANSLATE_MODULE.main()

    apply_auto.assert_not_called()


def test_auto_translate_main_updates_seed_file_and_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The CLI writes translated YAML and updates the hash marker when changes exist."""
    seed_file = tmp_path / "seed.yaml"
    seed_file.write_text("prompts: []\nsystem_categories: []\n", encoding="utf-8")
    service = SimpleNamespace(cache=SimpleNamespace(reset=Mock()), cache_stats=Mock(return_value="stats"))
    args = argparse.Namespace(
        seed_file=seed_file,
        source_locale="en",
        target_locales=["fr"],
        overwrite_existing=False,
        dry_run=False,
        force=False,
        reset_cache=False,
        show_cache_stats=False,
    )
    writes: list[str] = []

    def record_hash(file_hash: str) -> None:
        writes.append(file_hash)

    def translated_stats(_seed_payload: dict[str, object], **_kwargs: object) -> dict[str, int]:
        return {
            "prompts_translated": 1,
            "categories_translated": 0,
            "aliases_translated": 0,
            "total_operations": 1,
            "skipped_missing_source": 0,
        }

    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "parse_args", lambda: args)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "TranslationService", lambda: service)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "_compute_file_hash", lambda _path: "next-hash")
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "_read_last_hash", lambda: None)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "_write_hash", record_hash)
    monkeypatch.setattr(AUTO_TRANSLATE_MODULE, "apply_auto_translations", translated_stats)

    AUTO_TRANSLATE_MODULE.main()

    assert PROMPTS_LINE in seed_file.read_text(encoding="utf-8")
    assert writes == ["next-hash"]
