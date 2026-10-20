"""The reported version comes from pyproject.toml, with a fallback when it is unreadable."""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

import app

UNKNOWN = "0.0.0+unknown"
LOCK_PACKAGE = "backend"


def test_version_matches_pyproject() -> None:
    """The app reports the version written in pyproject.toml."""
    pyproject = tomllib.loads((Path(app.__file__).parents[1] / "pyproject.toml").read_text())
    assert app.__version__ == pyproject["project"]["version"]


def test_version_falls_back_when_pyproject_is_missing(tmp_path: Path) -> None:
    """A missing pyproject.toml gives the placeholder version, not a crash."""
    assert app._read_version(tmp_path / "pyproject.toml") == UNKNOWN  # noqa: SLF001


def test_version_falls_back_when_project_version_is_absent(tmp_path: Path) -> None:
    """A pyproject.toml without project.version gives the placeholder version."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.uv]\npackage = false\n")
    assert app._read_version(pyproject) == UNKNOWN  # noqa: SLF001


def test_version_matches_changelog_and_package_files() -> None:
    """pyproject.toml, both package.json files and the latest dated CHANGELOG release agree."""
    root = Path(app.__file__).parents[2]
    latest = re.search(
        r"^## \[(\d+\.\d+\.\d+)\] - \d{4}-\d{2}-\d{2}$",
        (root / "CHANGELOG.md").read_text(),
        re.MULTILINE,
    )
    assert latest is not None
    for package in ("package.json", "frontend/package.json"):
        assert json.loads((root / package).read_text())["version"] == app.__version__, package
    assert latest[1] == app.__version__


def test_version_matches_lock_and_changelog_links() -> None:
    """uv.lock and the CHANGELOG compare links follow the release too.

    `uv sync --frozen` in CI and the images never rewrites uv.lock, so a bump that skips
    `uv lock` would otherwise ship a lock that names the old version.
    """
    root = Path(app.__file__).parents[2]
    lock = tomllib.loads((root / "backend/uv.lock").read_text())
    backend = next(package for package in lock["package"] if package["name"] == LOCK_PACKAGE)
    assert backend["version"] == app.__version__

    changelog = (root / "CHANGELOG.md").read_text()
    version = re.escape(app.__version__)
    assert re.search(rf"^\[Unreleased\]: \S+/compare/v{version}\.\.\.HEAD$", changelog, re.MULTILINE)
    assert re.search(rf"^\[{version}\]: \S+", changelog, re.MULTILINE)
