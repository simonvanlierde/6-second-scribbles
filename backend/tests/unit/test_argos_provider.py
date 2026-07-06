"""Tests for the Argos translation provider."""

from __future__ import annotations

from pathlib import Path

from translation.argos_provider import ArgosTranslationProvider


class _ProviderHarness(ArgosTranslationProvider):
    installed_pairs: set[tuple[str, str]]
    available_packages: list[_FakePackage]
    argos_package: _FakeArgosPackage
    argos_translate: _FakeArgosTranslate

    def ensure_pair(self, from_locale: str, to_locale: str) -> None:
        self._ensure_pair(from_locale, to_locale)


def _make_provider() -> _ProviderHarness:
    provider = _ProviderHarness.__new__(_ProviderHarness)
    provider.installed_pairs = set()
    provider.available_packages = []
    provider.argos_package = _FakeArgosPackage()
    provider.argos_translate = _FakeArgosTranslate()
    return provider


class _FakeArgosPackage:
    """Minimal argos package stub that records install calls."""

    def __init__(self) -> None:
        self.install_paths: list[Path] = []

    def install_from_path(self, path: Path) -> None:
        self.install_paths.append(path)

    def assert_not_called(self) -> None:
        assert self.install_paths == []

    def assert_called_once_with(self, path: Path) -> None:
        assert self.install_paths == [path]


class _FakeArgosTranslate:
    """Minimal argos translate stub that can return or raise a configured result."""

    def __init__(self) -> None:
        self.translation: object | None = None
        self.error: Exception | None = None

    def get_translation_from_codes(self, _from_code: str, _to_code: str) -> object | None:
        if self.error is not None:
            raise self.error
        return self.translation


class _FakePackage:
    def __init__(self, from_code: str, to_code: str) -> None:
        self.from_code = from_code
        self.to_code = to_code
        self.download_paths: list[Path] = []

    def download(self) -> Path:
        path = Path("en_es.argosmodel")
        self.download_paths.append(path)
        return path

    def assert_called_once_with(self) -> None:
        assert self.download_paths == [Path("en_es.argosmodel")]


def _make_package(from_code: str, to_code: str) -> _FakePackage:
    return _FakePackage(from_code, to_code)


def test_ensure_pair_marks_existing_installed_translation() -> None:
    """Reuse an already-installed translation pair without reinstalling it."""
    provider = _make_provider()
    provider.argos_translate.translation = object()

    provider.ensure_pair("en", "es")

    assert ("en", "es") in provider.installed_pairs
    provider.argos_package.assert_not_called()


def test_ensure_pair_installs_when_translation_lookup_returns_none() -> None:
    """Install the matching package when no translation is already cached."""
    provider = _make_provider()
    package = _make_package("en", "es")
    provider.available_packages = [package]
    provider.argos_translate.translation = None

    provider.ensure_pair("en", "es")

    package.assert_called_once_with()
    provider.argos_package.assert_called_once_with(Path("en_es.argosmodel"))
    assert ("en", "es") in provider.installed_pairs


def test_ensure_pair_installs_when_translation_lookup_raises_attribute_error() -> None:
    """Install the matching package when the lookup helper is unavailable."""
    provider = _make_provider()
    package = _make_package("en", "es")
    provider.available_packages = [package]
    provider.argos_translate.error = AttributeError("missing language")

    provider.ensure_pair("en", "es")

    package.assert_called_once_with()
    provider.argos_package.assert_called_once_with(Path("en_es.argosmodel"))
    assert ("en", "es") in provider.installed_pairs
