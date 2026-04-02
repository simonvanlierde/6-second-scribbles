"""Database models for Six Second Scribbles."""
# spell-checker: ignore ondelete, onupdate

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Category(Base):
    """Category model - represents a card category (global or room-specific)."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(String(5), nullable=False, default="en")  # ISO 639-1 language code
    room_id: Mapped[str] = mapped_column(String(50), nullable=True)  # NULL = global, value = room-specific
    created_by: Mapped[str] = mapped_column(String(50), nullable=True)  # Player ID who created (for custom categories)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship
    cards: Mapped[list[Card]] = relationship("Card", back_populates="category", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("idx_category_difficulty", "difficulty"),
        Index("idx_category_name", "name"),
        Index("idx_category_room", "room_id"),
        Index("idx_category_language", "language"),
    )

    def __repr__(self):
        room_info = f", room='{self.room_id}'" if self.room_id else ""
        return f"<Category(id={self.id}, name='{self.name}', difficulty='{self.difficulty}'{room_info})>"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "difficulty": self.difficulty,
            "description": self.description,
            "language": self.language,
            "room_id": self.room_id,
            "created_by": self.created_by,
            "is_custom": self.room_id is not None,
        }


class Card(Base):
    """Card model - individual items within a category."""

    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    item: Mapped[str] = mapped_column(String(100), nullable=False)
    alternatives: Mapped[list] = mapped_column(JSON, nullable=True, default=list)  # Alternative spellings/names
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    # Relationship
    category: Mapped[Category] = relationship("Category", back_populates="cards")

    # Indexes
    __table_args__ = (
        Index("idx_card_category", "category_id"),
        Index("idx_card_item", "item"),
    )

    def __repr__(self):
        return f"<Card(id={self.id}, category_id={self.category_id}, item='{self.item}')>"

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "category_id": self.category_id,
            "item": self.item,
            "alternatives": self.alternatives or [],
        }
