"""Session-backed authentication services."""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.auth.security import hash_password, verify_password
from app.core.redis import create_session, delete_session, get_session_user_id
from app.users.models import User
from app.users.schemas import UserResponse

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


def _new_user_id() -> str:
    return secrets.token_hex(16)


def _new_guest_username() -> str:
    # 64 bits of entropy: at 32 bits (token_hex(4)) guest names collided against
    # the UNIQUE constraint around ~77k accounts, turning into intermittent 500s.
    return f"guest-{secrets.token_hex(8)}"


async def _commit_or_username_conflict(db: AsyncSession) -> None:
    """Commit, translating a username UNIQUE violation into a clean 409."""
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Username is already taken") from exc


async def create_guest_user(
    db: AsyncSession,
    *,
    preferred_locale: str,
    display_name: str | None,
) -> User:
    """Create a lightweight guest user, retrying on the rare username collision."""
    for _ in range(3):
        user = User(
            id=_new_user_id(),
            username=_new_guest_username(),
            display_name=display_name,
            preferred_locale=preferred_locale,
            password_hash=None,
        )
        db.add(user)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue
        return user
    raise HTTPException(status_code=500, detail="Could not allocate a guest account. Try again.")


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

    password_hash = hash_password(password)

    if current_user is not None and current_user.password_hash is None:
        current_user.username = username
        current_user.password_hash = password_hash
        current_user.preferred_locale = preferred_locale
        current_user.display_name = display_name
        await _commit_or_username_conflict(db)
        return current_user

    user = User(
        id=_new_user_id(),
        username=username,
        password_hash=password_hash,
        preferred_locale=preferred_locale,
        display_name=display_name,
    )
    db.add(user)
    await _commit_or_username_conflict(db)
    return user


async def login_user(db: AsyncSession, *, username: str, password: str) -> User:
    """Validate username/password credentials."""
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.password_hash):
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
    return UserResponse(
        id=user.id,
        username=user.username,
        displayName=user.display_name,
        preferredLocale=user.preferred_locale,
        isGuest=user.password_hash is None,
    )
