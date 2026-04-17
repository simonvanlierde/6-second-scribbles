"""Fast HTTP-level auth tests that do not need real Postgres or Redis."""

from __future__ import annotations

from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

from fastapi import HTTPException

from app.auth import dependencies as auth_dependencies
from app.auth import router as auth_router
from app.core import database
from app.main import application

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    import pytest
    from httpx import AsyncClient

SESSION_COOKIE_NAME = "scribbles_session"
AUTHENTICATED_MARKER = object()


async def _override_db() -> AsyncIterator[AsyncMock]:
    yield AsyncMock()


async def test_register_claims_guest_user_fast(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Register keeps its HTTP contract without real infra setup."""
    guest_user = SimpleNamespace(
        id="guest-1",
        username="guest-1",
        display_name="Guest",
        preferred_locale="en",
        password_hash=None,
    )
    registered_user = SimpleNamespace(
        id="guest-1",
        username="alice",
        display_name="Alice",
        preferred_locale="fr",
        password_hash=AUTHENTICATED_MARKER,
    )
    register_user = AsyncMock(return_value=registered_user)
    create_user_session = AsyncMock(return_value="session-token")
    enforce_rate_limit = AsyncMock()

    application.dependency_overrides[database.get_async_session] = _override_db
    application.dependency_overrides[auth_dependencies.get_optional_current_user] = lambda: guest_user
    monkeypatch.setattr(auth_router, "register_user", register_user)
    monkeypatch.setattr(auth_router, "create_user_session", create_user_session)
    monkeypatch.setattr(auth_router, "enforce_rate_limit", enforce_rate_limit)

    response = await async_client.post(
        "/api/auth/register",
        json={
            "username": "alice",
            "password": "supersecret",
            "preferredLocale": "fr",
            "displayName": "Alice",
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "guest-1",
        "username": "alice",
        "displayName": "Alice",
        "preferredLocale": "fr",
        "isGuest": False,
    }
    assert response.headers["set-cookie"].startswith(f"{SESSION_COOKIE_NAME}=")
    register_user.assert_awaited_once()
    create_user_session.assert_awaited_once_with(registered_user)
    enforce_rate_limit.assert_awaited_once()


async def test_update_preferences_updates_current_user_fast(
    async_client: AsyncClient,
) -> None:
    """Preference updates can stay on the fast app test path."""
    db = AsyncMock()
    current_user = SimpleNamespace(
        id="user-1",
        username="charlie",
        display_name="Before",
        preferred_locale="en",
        password_hash=AUTHENTICATED_MARKER,
    )

    async def override_db() -> AsyncIterator[AsyncMock]:
        yield db

    application.dependency_overrides[database.get_async_session] = override_db
    application.dependency_overrides[auth_dependencies.get_current_user] = lambda: current_user

    response = await async_client.patch(
        "/api/me/preferences",
        json={"preferredLocale": "nl", "displayName": "Charlie"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "id": "user-1",
        "username": "charlie",
        "displayName": "Charlie",
        "preferredLocale": "nl",
        "isGuest": False,
    }
    db.commit.assert_awaited_once()


async def test_login_rejects_invalid_password_fast(
    async_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid-credential responses do not need the integration stack."""
    monkeypatch.setattr(
        auth_router,
        "login_user",
        AsyncMock(side_effect=HTTPException(status_code=401, detail="Invalid username or password")),
    )
    monkeypatch.setattr(auth_router, "enforce_rate_limit", AsyncMock())
    application.dependency_overrides[database.get_async_session] = _override_db

    response = await async_client.post(
        "/api/auth/login",
        json={"username": "dora", "password": "wrongpass"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid username or password"}
