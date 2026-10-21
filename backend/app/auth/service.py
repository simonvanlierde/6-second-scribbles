"""Session-backed authentication services."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.core.config import settings
from app.core.redis import create_session, get_session_user_id
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


async def create_user_session(user: User) -> str:
    """Create and persist a new auth session."""
    return await create_session(user.id)


async def get_user_by_session(db: AsyncSession, session_id: str | None) -> User | None:
    """Resolve the current user from a Redis session id."""
    if not session_id:
        return None
    user_id = await get_session_user_id(session_id)
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def prune_expired_guests(db: AsyncSession) -> int:
    """Delete guest users whose session cookie has expired, and return how many went.

    A guest gets its only session when it is created, and that session never
    renews, so once ``updated_at`` is older than the session TTL nobody can act
    as that guest again. Registered users always have a password hash and are
    never touched.
    """
    cutoff = datetime.now(UTC) - timedelta(seconds=settings.auth_session_ttl_seconds)
    result = await db.execute(
        delete(User).where(User.password_hash.is_(None), User.updated_at < cutoff).returning(User.id)
    )
    await db.commit()
    return len(result.all())


def to_user_response(user: User) -> UserResponse:
    """Build a transport-safe user response."""
    return UserResponse(
        id=user.id,
        username=user.username,
        displayName=user.display_name,
        preferredLocale=user.preferred_locale,
        isGuest=user.password_hash is None,
    )
