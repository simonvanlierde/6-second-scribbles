"""Canonical multilingual category models (M2M)."""
# spell-checker: ignore ondelete, onupdate

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

_LOCALE_PATTERN = re.compile(r"^[a-z]{2,5}(?:-[a-z0-9]{2,8})?$")
_LOCALE_SEPARATOR = "-"
DEFAULT_CATEGORY_SOURCE = "system"


def normalize_locale_code(locale: str | None) -> str | None:
    """Normalize locale code for coverage metrics.

    We canonicalize casing while preserving region variants (for example,
    zh-cn -> zh-CN) so availability can distinguish playable regional content.
    """
    if not locale:
        return None

    raw = locale.strip().lower().replace("_", _LOCALE_SEPARATOR)
    if not raw or not _LOCALE_PATTERN.match(raw):
        return None

    if _LOCALE_SEPARATOR not in raw:
        return raw

    language, region = raw.split(_LOCALE_SEPARATOR, 1)
    return f"{language}{_LOCALE_SEPARATOR}{region.upper() if len(region) == 2 else region}"


class Category(Base):
    """Language-neutral category concept."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    default_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default=DEFAULT_CATEGORY_SOURCE)

    # Denormalized for instant listing of available categories per language
    available_locales: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    translations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    prompts: Mapped[list[CategoryPrompt]] = relationship(
        "CategoryPrompt",
        back_populates="category",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_category_difficulty", "difficulty"),
        Index("idx_category_slug", "slug"),
        Index("idx_category_available_locales", "available_locales", postgresql_using="gin"),
        Index("idx_category_translations", "translations", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Category(id={self.id}, difficulty='{self.difficulty}', source='{self.source}')>"


class Prompt(Base):
    """Global unique drawing concept (Global Prompt Library)."""

    __tablename__ = "prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stable_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    translations: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict, server_default="{}")
    categories: Mapped[list[CategoryPrompt]] = relationship(
        "CategoryPrompt",
        back_populates="prompt",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_prompt_stable_key", "stable_key"),
        Index("idx_prompt_translations", "translations", postgresql_using="gin"),
    )


class CategoryPrompt(Base):
    """Many-to-Many bridge between categories and prompts."""

    __tablename__ = "category_prompts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False)
    prompt_id: Mapped[int] = mapped_column(Integer, ForeignKey("prompts.id", ondelete="CASCADE"), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    category: Mapped[Category] = relationship("Category", back_populates="prompts")
    prompt: Mapped[Prompt] = relationship("Prompt", back_populates="categories")

    __table_args__ = (
        UniqueConstraint("category_id", "prompt_id", name="uq_category_prompt"),
        Index("idx_category_prompt_category", "category_id"),
        Index("idx_category_prompt_prompt", "prompt_id"),
    )


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def compute_available_locales(
    category_translations: dict[str, object] | None,
    prompt_translations: list[dict[str, object] | None],
) -> list[str]:
    """Compute the set of locales fully playable for a category.

    A locale is available only when the category has a valid translation AND
    every linked prompt has a valid translation in that locale. Previously
    maintained via a SQLAlchemy after_flush listener; now computed explicitly
    at seed time so model writes carry no runtime side effects.
    """
    category_locales: set[str] = set()
    for raw_locale, payload in (category_translations or {}).items():
        locale = normalize_locale_code(raw_locale)
        if not locale or not isinstance(payload, dict):
            continue
        typed_payload = cast("dict[str, object]", payload)
        if _is_non_empty_string(typed_payload.get("name")):
            category_locales.add(locale)

    if not category_locales or not prompt_translations:
        return []

    per_prompt_locales: list[set[str]] = []
    for translations in prompt_translations:
        locales: set[str] = set()
        for raw_locale, payload in (translations or {}).items():
            locale = normalize_locale_code(raw_locale)
            if not locale or not isinstance(payload, dict):
                continue
            typed_payload = cast("dict[str, object]", payload)
            label = typed_payload.get("label")
            aliases = typed_payload.get("aliases")
            if _is_non_empty_string(label) and (aliases is None or isinstance(aliases, list)):
                locales.add(locale)
        per_prompt_locales.append(locales)

    all_prompts_cover = set.intersection(*per_prompt_locales) if per_prompt_locales else set()
    return sorted(category_locales & all_prompts_cover)
