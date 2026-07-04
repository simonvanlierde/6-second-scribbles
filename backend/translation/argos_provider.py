"""Argos Translate provider for offline translation."""

from __future__ import annotations

import importlib
import logging

from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)


def _base_code(locale: str) -> str:
    """Reduce a region-tagged app locale to the base ISO 639 code Argos uses.

    Argos packages are keyed by base codes ('pt', 'es'), not region-tagged
    locales ('pt-BR'), so matching the full locale never found a package.
    """
    return locale.split("-", 1)[0].lower()


class ArgosTranslationProvider:
    """Wrapper around Argos Translate with package management."""

    def __init__(self) -> None:
        """Initialize the provider and update package index."""
        try:
            self.argos_package = importlib.import_module("argostranslate.package")
            self.argos_translate = importlib.import_module("argostranslate.translate")
        except ImportError as exc:
            msg = "Argos Translate is not installed. Run: uv sync --group db-translate or uv sync --all-groups"
            raise RuntimeError(msg) from exc

        logger.info("Updating Argos package index...")
        self.argos_package.update_package_index()
        self.available_packages = list(self.argos_package.get_available_packages())
        self.installed_pairs: set[tuple[str, str]] = set()

    def _ensure_pair(self, from_locale: str, to_locale: str) -> None:
        """Ensure translation model for language pair is available."""
        from_code, to_code = _base_code(from_locale), _base_code(to_locale)
        if (from_code, to_code) in self.installed_pairs:
            return
        try:
            translation = self.argos_translate.get_translation_from_codes(from_code, to_code)
        except AttributeError:
            translation = None

        if translation is not None:
            self.installed_pairs.add((from_code, to_code))
            return

        matching = [pkg for pkg in self.available_packages if pkg.from_code == from_code and pkg.to_code == to_code]
        if not matching:
            msg = f"No Argos package available for {from_code} -> {to_code}."
            raise RuntimeError(msg)

        logger.info("Installing Argos package %s -> %s", from_code, to_code)
        download_path = matching[0].download()
        self.argos_package.install_from_path(download_path)
        self.installed_pairs.add((from_code, to_code))

    def translate(self, from_locale: str, to_locale: str, text: str) -> str:
        """Translate text from one locale to another."""
        from_code, to_code = _base_code(from_locale), _base_code(to_locale)
        if from_code == to_code:
            return text
        self._ensure_pair(from_locale, to_locale)
        translation = self.argos_translate.get_translation_from_codes(from_code, to_code)
        if translation is None:
            msg = f"No Argos translation available for {from_code} -> {to_code}."
            raise RuntimeError(msg)
        result = translation.translate(text)
        return result.strip() if result else text

    def prefetch_pairs(self, from_locale: str, to_locales: list[str]) -> None:
        """Pre-download all language pair models."""
        for to_locale in to_locales:
            self._ensure_pair(from_locale, to_locale)
