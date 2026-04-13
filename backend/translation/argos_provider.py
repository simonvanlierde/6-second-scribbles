"""Argos Translate provider for offline translation."""

from __future__ import annotations

import logging

from argostranslate import package as argos_package
from argostranslate import translate as argos_translate

from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


class ArgosTranslationProvider:
    """Wrapper around Argos Translate with package management."""

    def __init__(self) -> None:
        """Initialize the provider and update package index."""
        try:
            self.argos_package = argos_package
            self.argos_translate = argos_translate
        except ImportError as exc:
            msg = "Argos Translate is not installed. Run: uv sync --all-groups"
            raise RuntimeError(msg) from exc

        logger.info("Updating Argos package index...")
        self.argos_package.update_package_index()
        self.available_packages = list(self.argos_package.get_available_packages())
        self.installed_pairs: set[tuple[str, str]] = set()

    def _ensure_pair(self, from_locale: str, to_locale: str) -> None:
        """Ensure translation model for language pair is available."""
        if (from_locale, to_locale) in self.installed_pairs:
            return
        try:
            self.argos_translate.get_translation_from_codes(from_locale, to_locale)
            self.installed_pairs.add((from_locale, to_locale))
        except Exception:
            pass
        else:
            return

        matching = [pkg for pkg in self.available_packages if pkg.from_code == from_locale and pkg.to_code == to_locale]
        if not matching:
            msg = f"No Argos package available for {from_locale} -> {to_locale}."
            raise RuntimeError(msg)

        logger.info("Installing Argos package %s -> %s", from_locale, to_locale)
        download_path = matching[0].download()
        self.argos_package.install_from_path(download_path)
        self.installed_pairs.add((from_locale, to_locale))

    def translate(self, from_locale: str, to_locale: str, text: str) -> str:
        """Translate text from one locale to another."""
        if from_locale == to_locale:
            return text
        self._ensure_pair(from_locale, to_locale)
        translation = self.argos_translate.get_translation_from_codes(from_locale, to_locale)
        result = translation.translate(text)
        return result.strip() if result else text

    def prefetch_pairs(self, from_locale: str, to_locales: list[str]) -> None:
        """Pre-download all language pair models."""
        for to_locale in to_locales:
            self._ensure_pair(from_locale, to_locale)
