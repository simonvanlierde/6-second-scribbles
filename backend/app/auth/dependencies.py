"""Reusable auth dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Cookie, Depends, HTTPException

from app.auth.service import get_user_by_session
from app.core.config import settings
from app.core.database import AsyncSessionDep
from app.users.models import User


async def get_current_user(
    db: AsyncSessionDep,
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User:
    """Return the authenticated user or fail."""
    user = await get_user_by_session(db, session_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


async def get_optional_current_user(
    db: AsyncSessionDep,
    session_id: str | None = Cookie(default=None, alias=settings.session_cookie_name),
) -> User | None:
    """Return the authenticated user when a valid session exists."""
    return await get_user_by_session(db, session_id)


CurrentUserDep = Annotated[User, Depends(get_current_user)]
OptionalCurrentUserDep = Annotated[User | None, Depends(get_optional_current_user)]
