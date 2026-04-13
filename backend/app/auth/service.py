"""Session-backed authentication services."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select

from app.auth.security import password_service
from app.core.redis import create_session, delete_session, get_session_user_id
from app.users.models import User
from app.users.schemas import UserResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _serialize_user(user: User) -> UserResponse:
    return UserResponse(
        id=user.id,
        username=user.username,
        display_name=user.display_name,
        preferredLocale=user.preferred_locale,
        isGuest=user.password_hash is None,
    )


def _new_user_id() -> str:
    return secrets.token_hex(16)


def _new_guest_username() -> str:
    return f"guest-{secrets.token_hex(4)}"


async def create_guest_user(
    db: AsyncSession,
    *,
    preferred_locale: str,
    display_name: str | None,
) -> User:
    """Create a lightweight guest user."""
    user = User(
        id=_new_user_id(),
        username=_new_guest_username(),
        display_name=display_name,
        preferred_locale=preferred_locale,
        password_hash=None,
    )
    db.add(user)
    await db.commit()
    return user


async def register_user(
    db: AsyncSession,
    *,
    username: str,
    password: str,
    preferred_locale: str,
    display_name: str | None,
    current_user: User | None,
) -> User:
    """Register a new account or claim the current guest account."""
    existing = await db.execute(select(User).where(User.username == username))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=409, detail="Username is already taken")

    password_hash = password_service.hash_password(password)

    if current_user is not None and current_user.password_hash is None:
        current_user.username = username
        current_user.password_hash = password_hash
        current_user.preferred_locale = preferred_locale
        current_user.display_name = display_name
        await db.commit()
        return current_user

    user = User(
        id=_new_user_id(),
        username=username,
        password_hash=password_hash,
        preferred_locale=preferred_locale,
        display_name=display_name,
    )
    db.add(user)
    await db.commit()
    return user


async def login_user(db: AsyncSession, *, username: str, password: str) -> User:
    """Validate username/password credentials."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not password_service.verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    return user


async def create_user_session(user: User) -> str:
    """Create and persist a new auth session."""
    return await create_session(user.id)


async def logout_session(session_id: str | None) -> None:
    """Delete an auth session if present."""
    if session_id:
        await delete_session(session_id)


async def get_user_by_session(db: AsyncSession, session_id: str | None) -> User | None:
    """Resolve the current user from a Redis session id."""
    if not session_id:
        return None
    user_id = await get_session_user_id(session_id)
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def to_user_response(user: User) -> UserResponse:
    """Build a transport-safe user response."""
    return _serialize_user(user)
