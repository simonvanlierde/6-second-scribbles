"""Guards on Alembic migrations that cannot run in reverse."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_VERSIONS = Path(__file__).resolve().parents[2] / "alembic" / "versions"


def test_jsonb_translations_migration_refuses_to_downgrade() -> None:
    """Downgrading past the JSONB migration stops with advice instead of emptying the translations."""
    path = next(_VERSIONS.glob("*-b2a7f484d1a9_*.py"))
    spec = importlib.util.spec_from_file_location("b2a7f484d1a9_jsonb_translations", path)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    with pytest.raises(NotImplementedError, match="restore a backup or re-seed"):
        migration.downgrade()
