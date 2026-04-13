"""Persistent translation cache backed by JSON file."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_CACHE_PATH = Path(__file__).parent / ".translation_cache.json"


@dataclass
class CacheStats:
    """Statistics about cache usage."""

    total_hits: int = 0
    total_misses: int = 0
    total_writes: int = 0

    @property
    def hit_rate(self) -> float:
        """Return cache hit rate as percentage."""
        total = self.total_hits + self.total_misses
        return (self.total_hits / total * 100) if total > 0 else 0

    def format_summary(self) -> str:
        """Return human-readable summary."""
        total = self.total_hits + self.total_misses
        return f"Cache hit rate: {self.hit_rate:.1f}% ({self.total_hits}/{total} hits) | writes: {self.total_writes}"


class PersistentTranslationCache:
    """JSON-backed translation cache for (from_locale, to_locale, text) → translation."""

    def __init__(self, cache_path: Path = DEFAULT_CACHE_PATH) -> None:
        """Initialize cache with optional path override."""
        self.cache_path = cache_path
        self.cache: dict[str, dict[str, str]] = self._load()
        self.stats = CacheStats()

    def _load(self) -> dict[str, dict[str, str]]:
        """Load cache from disk or return empty dict."""
        if not self.cache_path.exists():
            return {}
        try:
            content = self.cache_path.read_text(encoding="utf-8")
            return json.loads(content) if content else {}
        except OSError, json.JSONDecodeError:
            logger.warning("Failed to load cache from %s, starting fresh", self.cache_path)
            return {}

    def _make_key(self, from_locale: str, to_locale: str, text: str) -> str:
        """Create a cache key from locale pair and text."""
        return f"{from_locale}→{to_locale}|{text}"

    def get(self, from_locale: str, to_locale: str, text: str) -> str | None:
        """Retrieve cached translation or None if not found."""
        key = self._make_key(from_locale, to_locale, text)
        if key in self.cache.get(from_locale, {}):
            self.stats.total_hits += 1
            return self.cache[from_locale].get(key)
        self.stats.total_misses += 1
        return None

    def put(self, from_locale: str, to_locale: str, text: str, translation: str) -> None:
        """Store translation in cache and persist to disk."""
        self.cache.setdefault(from_locale, {})[self._make_key(from_locale, to_locale, text)] = translation
        self.stats.total_writes += 1
        self._save()

    def _save(self) -> None:
        """Persist cache to disk."""
        try:
            self.cache_path.write_text(json.dumps(self.cache, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to save cache to %s: %s", self.cache_path, exc)

    def reset(self) -> None:
        """Clear cache and remove file."""
        self.cache.clear()
        self.stats = CacheStats()
        if self.cache_path.exists():
            self.cache_path.unlink()
        logger.info("Translation cache reset")

    def stats_summary(self) -> str:
        """Return formatted stats summary."""
        return self.stats.format_summary()
