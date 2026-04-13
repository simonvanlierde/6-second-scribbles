"""Tests for first-party auth and session-backed user endpoints."""

from __future__ import annotations

from app.core.config import settings


async def test_guest_auth_creates_session_and_me_endpoint(async_client) -> None:
    guest_response = await async_client.post(
        "/api/auth/guest",
        json={"preferredLocale": "es", "displayName": "Sketch Friend"},
    )

    assert guest_response.status_code == 200
    payload = guest_response.json()
    assert payload["username"].startswith("guest-")
    assert payload["preferredLocale"] == "es"
    assert payload["displayName"] == "Sketch Friend"
    assert payload["isGuest"] is True

    # Verify session cookie is set with configured SameSite mode
    set_cookie = guest_response.headers["set-cookie"]
    assert "scribbles_session=" in set_cookie
    assert f"samesite={settings.session_cookie_same_site.lower()}" in set_cookie.lower()

    me_response = await async_client.get("/api/me")

    assert me_response.status_code == 200
    assert me_response.json()["id"] == payload["id"]


async def test_register_claims_guest_user(async_client) -> None:
    guest_response = await async_client.post("/api/auth/guest", json={"preferredLocale": "en"})
    guest_id = guest_response.json()["id"]

    register_response = await async_client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "supersecret",
            "preferredLocale": "fr",
            "displayName": "Alice",
        },
    )

    assert register_response.status_code == 200
    payload = register_response.json()
    assert payload["id"] == guest_id
    assert payload["username"] == "alice"
    assert payload["preferredLocale"] == "fr"
    assert payload["isGuest"] is False


async def test_login_logout_and_me_flow(async_client) -> None:
    register_response = await async_client.post(
        "/api/auth/register",
        json={
            "username": "bob",
            "password": "verysecure",
            "preferredLocale": "en",
        },
    )
    assert register_response.status_code == 200

    logout_response = await async_client.post("/api/auth/logout")
    assert logout_response.status_code == 204

    unauthorized_me = await async_client.get("/api/me")
    assert unauthorized_me.status_code == 401

    login_response = await async_client.post(
        "/api/auth/login",
        json={"username": "bob", "password": "verysecure"},
    )

    assert login_response.status_code == 200
    assert login_response.json()["username"] == "bob"

    me_response = await async_client.get("/api/me")
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "bob"


async def test_update_preferences_updates_current_user(async_client) -> None:
    await async_client.post(
        "/api/auth/register",
        json={"username": "charlie", "password": "super_secure", "preferredLocale": "en"},
    )

    update_response = await async_client.patch(
        "/api/me/preferences",
        json={"preferredLocale": "nl", "displayName": "Charlie"},
    )

    assert update_response.status_code == 200
    payload = update_response.json()
    assert payload["preferredLocale"] == "nl"
    assert payload["displayName"] == "Charlie"


async def test_login_rejects_invalid_password(async_client) -> None:
    await async_client.post(
        "/api/auth/register",
        json={"username": "dora", "password": "password123", "preferredLocale": "en"},
    )
    await async_client.post("/api/auth/logout")

    login_response = await async_client.post(
        "/api/auth/login",
        json={"username": "dora", "password": "wrongpass"},
    )

    assert login_response.status_code == 401
    assert login_response.json() == {"detail": "Invalid username or password"}


async def test_guest_auth_is_rate_limited(async_client, monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_guest_rate_limit", 1)
    monkeypatch.setattr(settings, "auth_guest_rate_window_seconds", 60)

    first_response = await async_client.post("/api/auth/guest", json={"preferredLocale": "en"})
    second_response = await async_client.post("/api/auth/guest", json={"preferredLocale": "en"})

    assert first_response.status_code == 200
    assert second_response.status_code == 429
