"""Database model for application users."""
# spell-checker: ignore onupdate

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    """Persistent application user."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    username: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    preferred_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("idx_users_username", "username", unique=True),
        Index("idx_users_preferred_locale", "preferred_locale"),
    )

    def __repr__(self) -> str:
        return f"<User(id='{self.id}', username='{self.username}')>"
