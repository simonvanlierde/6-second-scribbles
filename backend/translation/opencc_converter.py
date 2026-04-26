"""OpenCC-based conversion between Chinese locale variants."""

from __future__ import annotations

import importlib
from typing import Any, ClassVar, Protocol

ZH_CN = "zh-CN"
ZH_TW = "zh-TW"


class LocaleConverter(Protocol):
    """Protocol for deterministic same-language locale conversion."""

    def can_convert(self, from_locale: str, to_locale: str) -> bool:
        """Return whether this converter handles the locale pair."""

    def convert(self, from_locale: str, to_locale: str, text: str) -> str:
        """Convert text between locale variants."""


class OpenCCLocaleConverter:
    """Convert between Simplified and Traditional Chinese with OpenCC."""

    _CONFIGS: ClassVar[dict[tuple[str, str], str]] = {
        (ZH_CN, ZH_TW): "s2tw",
        (ZH_TW, ZH_CN): "tw2s",
    }

    def __init__(self) -> None:
        self._converters: dict[tuple[str, str], Any] = {}

    def can_convert(self, from_locale: str, to_locale: str) -> bool:
        """Return whether OpenCC supports this locale pair."""
        return (from_locale, to_locale) in self._CONFIGS

    def convert(self, from_locale: str, to_locale: str, text: str) -> str:
        """Convert Chinese text between Simplified and Traditional variants."""
        pair = (from_locale, to_locale)
        config = self._CONFIGS.get(pair)
        if config is None:
            msg = f"OpenCC conversion is not configured for {from_locale} -> {to_locale}."
            raise RuntimeError(msg)

        converter = self._converters.get(pair)
        if converter is None:
            try:
                opencc_module = importlib.import_module("opencc")
            except ImportError as exc:
                msg = (
                    "OpenCC is not installed. Run: uv sync --group db-translate or uv sync --all-groups "
                    "before translating Chinese locale variants."
                )
                raise RuntimeError(msg) from exc
            converter = opencc_module.OpenCC(config)
            self._converters[pair] = converter

        result = converter.convert(text)
        return result.strip() if result else text
