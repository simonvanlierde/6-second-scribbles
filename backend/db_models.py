"""
Database models for Six Second Scribbles
"""
from datetime import datetime
from typing import List
from sqlalchemy import String, Integer, DateTime, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class Category(Base):
    """Category model - represents a card category"""
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    # Relationship
    cards: Mapped[List["Card"]] = relationship(
        "Card", back_populates="category", cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        Index("idx_category_difficulty", "difficulty"),
        Index("idx_category_name", "name"),
    )

    def __repr__(self):
        return f"<Category(id={self.id}, name='{self.name}', difficulty='{self.difficulty}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "difficulty": self.difficulty,
            "description": self.description,
            "item_count": len(self.cards) if self.cards else 0,
        }


class Card(Base):
    """Card model - individual items within a category"""
    __tablename__ = "cards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False
    )
    item: Mapped[str] = mapped_column(String(100), nullable=False)
    alternatives: Mapped[list] = mapped_column(JSON, nullable=True, default=list)  # Alternative spellings/names
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationship
    category: Mapped["Category"] = relationship("Category", back_populates="cards")

    # Indexes
    __table_args__ = (
        Index("idx_card_category", "category_id"),
        Index("idx_card_item", "item"),
    )

    def __repr__(self):
        return f"<Card(id={self.id}, category_id={self.category_id}, item='{self.item}')>"

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "category_id": self.category_id,
            "item": self.item,
            "alternatives": self.alternatives or [],
        }


class GameSession(Base):
    """Optional: Game session tracking for analytics"""
    __tablename__ = "game_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_code: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    player_count: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    rounds: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    final_scores: Mapped[dict] = mapped_column(JSON, nullable=True)

    __table_args__ = (
        Index("idx_session_room", "room_code"),
        Index("idx_session_started", "started_at"),
    )

    def __repr__(self):
        return f"<GameSession(id={self.id}, room_code='{self.room_code}', players={self.player_count})>"
