"""Tests for the shared logging setup."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from app.core import logging as app_logging

if TYPE_CHECKING:
    import pytest

ACCESS_LOGGER = "uvicorn.access"


def test_prod_logging_drops_uvicorn_access_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """In prod the access log would carry each visitor's full IP, so it is switched off."""
    access = logging.getLogger(ACCESS_LOGGER)
    monkeypatch.setattr(access, "disabled", False)
    monkeypatch.setattr(app_logging, "IS_PROD", True)

    app_logging.configure_logging()

    assert access.disabled is True


def test_dev_logging_keeps_uvicorn_access_lines(monkeypatch: pytest.MonkeyPatch) -> None:
    """Outside prod the access log stays on for local debugging."""
    access = logging.getLogger(ACCESS_LOGGER)
    monkeypatch.setattr(access, "disabled", False)
    monkeypatch.setattr(app_logging, "IS_PROD", False)

    app_logging.configure_logging()

    assert access.disabled is False
