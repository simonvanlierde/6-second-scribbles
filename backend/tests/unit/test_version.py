"""The reported version comes from pyproject.toml, with a fallback when it is unreadable."""

from __future__ import annotations

import tomllib
from pathlib import Path

import app

UNKNOWN = "0.0.0+unknown"


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
