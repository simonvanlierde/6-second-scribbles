"""High-level translation service with caching and provider abstraction."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from translation.argos_provider import ArgosTranslationProvider
from translation.cache import PersistentTranslationCache

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class TranslationService:
    """Unified translation service with cache, provider, and deduplication."""

    def __init__(
        self,
        provider_class: type | None = None,
        cache_path: Path | None = None,
    ) -> None:
        """Initialize service with optional provider and cache path overrides."""
        self.provider = (provider_class or ArgosTranslationProvider)()
        self.cache = PersistentTranslationCache(cache_path) if cache_path else PersistentTranslationCache()
        self.session_cache: dict[tuple[str, str, str], str] = {}  # In-memory deduplication within session

    def translate(self, from_locale: str, to_locale: str, text: str) -> str:
        """Translate text with multi-level caching (session → persistent → provider)."""
        # Same locale, no-op
        if from_locale == to_locale:
            return text

        # Session cache hit
        key = (from_locale, to_locale, text)
        if key in self.session_cache:
            return self.session_cache[key]

        # Persistent cache hit
        cached = self.cache.get(from_locale, to_locale, text)
        if cached:
            self.session_cache[key] = cached
            return cached

        # Provider
        result = self.provider.translate(from_locale, to_locale, text)
        self.cache.put(from_locale, to_locale, text, result)
        self.session_cache[key] = result
        return result

    def prefetch_pairs(self, from_locale: str, to_locales: list[str]) -> None:
        """Pre-download all language pair models."""
        self.provider.prefetch_pairs(from_locale, to_locales)

    def reset_cache(self) -> None:
        """Clear all caches."""
        self.session_cache.clear()
        self.cache.reset()

    def cache_stats(self) -> str:
        """Return formatted cache statistics."""
        return self.cache.stats_summary()
