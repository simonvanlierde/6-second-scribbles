"""Tests for guest auth and the session-backed /me endpoint."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from app.core.config import settings

if TYPE_CHECKING:
    from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

PRELOADED_LOCALE = "es"
DISPLAY_NAME = "Sketch Friend"
SESSION_COOKIE_PREFIX = "scribbles_session="
SAME_SITE_LAX = "samesite=lax"
LOCALE_EN = "en"


async def test_guest_auth_creates_session_and_me_endpoint(async_client: AsyncClient) -> None:
    """Guest auth creates a session and returns the current user on /me."""
    guest_response = await async_client.post(
        "/api/auth/guest",
        json={"preferredLocale": PRELOADED_LOCALE, "displayName": DISPLAY_NAME},
    )

    assert guest_response.status_code == 200
    payload = guest_response.json()
    assert payload["username"].startswith("guest-")
    assert payload["preferredLocale"] == PRELOADED_LOCALE
    assert payload["displayName"] == DISPLAY_NAME
    assert payload["isGuest"]

    set_cookie = guest_response.headers["set-cookie"]
    assert SESSION_COOKIE_PREFIX in set_cookie
    assert SAME_SITE_LAX in set_cookie.lower()

    me_response = await async_client.get("/api/me")

    assert me_response.status_code == 200
    assert me_response.json()["id"] == payload["id"]


async def test_guest_auth_is_rate_limited(async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Guest auth hits the configured rate limit."""
    monkeypatch.setattr(settings, "auth_guest_rate_limit", 1)
    monkeypatch.setattr(settings, "auth_guest_rate_window_seconds", 60)

    first_response = await async_client.post("/api/auth/guest", json={"preferredLocale": LOCALE_EN})
    second_response = await async_client.post("/api/auth/guest", json={"preferredLocale": LOCALE_EN})

    assert first_response.status_code == 200
    assert second_response.status_code == 429
