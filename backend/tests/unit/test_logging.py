"""Tests for the shared logging setup."""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING

from app.core import logging as app_logging

if TYPE_CHECKING:
    import pytest

ACCESS_LOGGER = "uvicorn.access"
CLIENT_IP = "203.0.113.7"


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


def test_prod_logging_drops_websocket_handshake_lines(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """Uvicorn logs each WebSocket handshake with the full client IP on its error logger."""
    monkeypatch.setattr(app_logging, "IS_PROD", True)
    uvicorn_logger = logging.getLogger("uvicorn")
    # Uvicorn's own logging config gives this logger a plain handler before the app loads.
    uvicorn_logger.addHandler(logging.StreamHandler(sys.stderr))
    root_handlers = logging.getLogger().handlers[:]
    try:
        app_logging.configure_logging()
        error_log = logging.getLogger("uvicorn.error")
        error_log.info('%s - "WebSocket %s" [accepted]', f"{CLIENT_IP}:0", "/ws/ABCDEF")
        error_log.info("Application startup complete.")
    finally:
        uvicorn_logger.handlers.clear()
        # The new root handler writes to capsys's stream, which closes after this test.
        logging.getLogger().handlers[:] = root_handlers

    err = capsys.readouterr().err
    assert CLIENT_IP not in err
    assert err.count("Application startup complete.") == 1
