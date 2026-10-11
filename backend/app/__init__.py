"""FastAPI backend for Six Second Scribbles."""

import tomllib
from pathlib import Path


def _read_version(pyproject: Path = Path(__file__).parents[1] / "pyproject.toml") -> str:
    # NOTE: uv treats this project as virtual (no build backend), so it is never
    # installed and has no package metadata. Read the pyproject.toml that sits
    # next to app/ instead; the prod image copies it in for this.
    try:
        return tomllib.loads(pyproject.read_text())["project"]["version"]
    except OSError, KeyError:
        return "0.0.0+unknown"


__version__ = _read_version()
