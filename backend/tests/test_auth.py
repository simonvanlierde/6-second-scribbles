"""Tests for first-party auth and session-backed user endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.config import settings

if TYPE_CHECKING:
    import pytest
    from httpx import AsyncClient

PRELOADED_LOCALE = "es"
DISPLAY_NAME = "Sketch Friend"
SESSION_COOKIE_PREFIX = "scribbles_session="
USERNAME_ALICE = "alice"
USERNAME_BOB = "bob"
USERNAME_CHARLIE = "charlie"
SECRET_ALICE = "supersecret"  # noqa: S105
SECRET_BOB = "verysecure"  # noqa: S105
SECRET_INVALID = "wrongpass"  # noqa: S105
SECRET_CHARLIE = "super_secure"  # noqa: S105
LOCALE_EN = "en"
LOCALE_FR = "fr"
LOCALE_NL = "nl"
DISPLAY_CHARLIE = "Charlie"


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
    assert f"samesite={settings.session_cookie_same_site.lower()}" in set_cookie.lower()

    me_response = await async_client.get("/api/me")

    assert me_response.status_code == 200
    assert me_response.json()["id"] == payload["id"]


async def test_register_claims_guest_user(async_client: AsyncClient) -> None:
    """Registering claims the existing guest account."""
    guest_response = await async_client.post("/api/auth/guest", json={"preferredLocale": LOCALE_EN})
    guest_id = guest_response.json()["id"]

    register_response = await async_client.post(
        "/api/auth/register",
        json={
            "username": USERNAME_ALICE,
            "password": SECRET_ALICE,
            "preferredLocale": LOCALE_FR,
            "displayName": "Alice",
        },
    )

    assert register_response.status_code == 200
    payload = register_response.json()
    assert payload["id"] == guest_id
    assert payload["username"] == USERNAME_ALICE
    assert payload["preferredLocale"] == LOCALE_FR
    assert not payload["isGuest"]


async def test_login_logout_and_me_flow(async_client: AsyncClient) -> None:
    """Login, logout, and /me all round-trip as expected."""
    register_response = await async_client.post(
        "/api/auth/register",
        json={
            "username": USERNAME_BOB,
            "password": SECRET_BOB,
            "preferredLocale": LOCALE_EN,
        },
    )
    assert register_response.status_code == 200

    logout_response = await async_client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    unauthorized_me = await async_client.get("/api/me")
    assert unauthorized_me.status_code == 401

    login_response = await async_client.post(
        "/api/auth/login",
        json={"username": USERNAME_BOB, "password": SECRET_BOB},
    )

    assert login_response.status_code == 200
    assert login_response.json()["username"] == USERNAME_BOB

    me_response = await async_client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == USERNAME_BOB


async def test_update_preferences_updates_current_user(async_client: AsyncClient) -> None:
    """Updating preferences persists the new locale and display name."""
    await async_client.post(
        "/api/auth/register",
        json={"username": USERNAME_CHARLIE, "password": SECRET_CHARLIE, "preferredLocale": LOCALE_EN},
    )

    update_response = await async_client.patch(
        "/api/me/preferences",
        json={"preferredLocale": LOCALE_NL, "displayName": DISPLAY_CHARLIE},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["preferredLocale"] == LOCALE_NL
    assert payload["displayName"] == DISPLAY_CHARLIE


async def test_login_rejects_invalid_password(async_client: AsyncClient) -> None:
    """Invalid credentials are rejected."""
    await async_client.post(
        "/api/auth/register",
        json={"username": "dora", "password": "password123", "preferredLocale": LOCALE_EN},
    )
    await async_client.post("/api/auth/logout")

    login_response = await async_client.post(
        "/api/auth/login",
        json={"username": "dora", "password": SECRET_INVALID},
    )

    assert login_response.status_code == 401
    assert login_response.json() == {"detail": "Invalid username or password"}


async def test_guest_auth_is_rate_limited(async_client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Guest auth hits the configured rate limit."""
    monkeypatch.setattr(settings, "auth_guest_rate_limit", 1)
    monkeypatch.setattr(settings, "auth_guest_rate_window_seconds", 60)

    first_response = await async_client.post("/api/auth/guest", json={"preferredLocale": LOCALE_EN})
    second_response = await async_client.post("/api/auth/guest", json={"preferredLocale": LOCALE_EN})

    assert first_response.status_code == 200
    assert second_response.status_code == 429
