"""Database models for category and card data."""
# spell-checker: ignore ondelete, onupdate

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Category(Base):
    """Category model representing a global or room-specific card category."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="en")
    room_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    cards: Mapped[list[Card]] = relationship("Card", back_populates="category", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_category_difficulty", "difficulty"),
        Index("idx_category_name", "name"),
        Index("idx_category_room", "room_id"),
        Index("idx_category_language", "language"),
    )

    def __repr__(self) -> str:
        room_info = f", room='{self.room_id}'" if self.room_id else ""
        return f"<Category(id={self.id}, name='{self.name}', difficulty='{self.difficulty}'{room_info})>"


class Card(Base):
    """Card model representing one drawable/guessable item in a category."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    item: Mapped[str] = mapped_column(String(100), nullable=False)
    alternatives: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    category: Mapped[Category] = relationship("Category", back_populates="cards")

    __table_args__ = (
        Index("idx_card_category", "category_id"),
        Index("idx_card_item", "item"),
    )

    def __repr__(self) -> str:
        return f"<Card(id={self.id}, category_id={self.category_id}, item='{self.item}')>"
