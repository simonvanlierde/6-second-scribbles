"""Tests for translation service locale conversion behavior."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from translation.service import TranslationService

if TYPE_CHECKING:
    import pytest

OPENCC_ANIMALS = "动物<opencc:zh-CN->zh-TW>"


class DummyProvider:
    """Translation provider that records calls and returns predictable output."""

    def __init__(self) -> None:
        self.translate_calls: list[tuple[str, str, str]] = []
        self.prefetch_calls: list[tuple[str, list[str]]] = []

    def translate(self, from_locale: str, to_locale: str, text: str) -> str:
        """Return predictable translated text."""
        self.translate_calls.append((from_locale, to_locale, text))
        return f"{text}<{from_locale}->{to_locale}>"

    def prefetch_pairs(self, from_locale: str, to_locales: list[str]) -> None:
        """Record prefetch requests."""
        self.prefetch_calls.append((from_locale, to_locales))


class DummyCache:
    """No-op cache for TranslationService tests."""

    def __init__(self, _cache_path: object | None = None) -> None:
        self.values: dict[tuple[str, str, str], str] = {}

    def get(self, from_locale: str, to_locale: str, text: str) -> str | None:
        """Get a cached translation."""
        return self.values.get((from_locale, to_locale, text))

    def put(self, from_locale: str, to_locale: str, text: str, result: str) -> None:
        """Store a cached translation."""
        self.values[(from_locale, to_locale, text)] = result

    def reset(self) -> None:
        """Clear cached translations."""
        self.values.clear()

    def stats_summary(self) -> str:
        """Return a deterministic summary."""
        return "dummy cache"


class FakeOpenCCConverter:
    """Fake OpenCC converter for deterministic unit tests."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    def can_convert(self, from_locale: str, to_locale: str) -> bool:
        """Report support for Simplified-to-Traditional conversion."""
        return (from_locale, to_locale) == ("zh-CN", "zh-TW")

    def convert(self, from_locale: str, to_locale: str, text: str) -> str:
        """Return predictable converted text."""
        self.calls.append((from_locale, to_locale, text))
        return f"{text}<opencc:{from_locale}->{to_locale}>"


def test_translation_service_uses_opencc_converter_before_provider(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chinese variant conversion bypasses the provider and uses OpenCC."""
    monkeypatch.setattr("translation.service.PersistentTranslationCache", DummyCache)
    converter = FakeOpenCCConverter()
    service = TranslationService(provider_class=DummyProvider, locale_converter=converter)

    result = service.translate("zh-CN", "zh-TW", "动物")
    provider = cast("DummyProvider", service.provider)

    assert result == OPENCC_ANIMALS
    assert converter.calls == [("zh-CN", "zh-TW", "动物")]
    assert provider.translate_calls == []


def test_translation_service_prefetch_skips_opencc_conversion_pairs(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prefetch only asks the provider for pairs OpenCC cannot handle."""
    monkeypatch.setattr("translation.service.PersistentTranslationCache", DummyCache)
    converter = FakeOpenCCConverter()
    service = TranslationService(provider_class=DummyProvider, locale_converter=converter)

    service.prefetch_pairs("zh-CN", ["zh-TW", "fr"])
    provider = cast("DummyProvider", service.provider)

    assert provider.prefetch_calls == [("zh-CN", ["fr"])]
