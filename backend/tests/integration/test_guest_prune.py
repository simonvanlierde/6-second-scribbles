"""Tests for deleting guest users whose session has expired."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest
from sqlalchemy import select

from app.auth.service import prune_expired_guests
from app.core.config import settings
from app.users.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio(loop_scope="session")]

OLD_GUEST = "old-guest"
NEW_GUEST = "new-guest"
OLD_MEMBER = "old-member"
MEMBER_HASH = "hash"


async def test_prune_deletes_only_expired_guests(db_session: AsyncSession) -> None:
    """Expired guests go; fresh guests and registered users of any age stay."""
    expired = datetime.now(UTC) - timedelta(seconds=settings.auth_session_ttl_seconds + 60)
    db_session.add_all(
        [
            User(id=OLD_GUEST, username=OLD_GUEST, password_hash=None, updated_at=expired),
            User(id=NEW_GUEST, username=NEW_GUEST, password_hash=None),
            User(id=OLD_MEMBER, username=OLD_MEMBER, password_hash=MEMBER_HASH, updated_at=expired),
        ]
    )
    await db_session.commit()

    assert await prune_expired_guests(db_session) == 1

    remaining = set((await db_session.execute(select(User.id))).scalars())
    assert {NEW_GUEST, OLD_MEMBER} <= remaining
    assert OLD_GUEST not in remaining
