"""Canonical multilingual category models (M2M + Auto-Sync Locales)."""
# spell-checker: ignore ondelete, onupdate

from __future__ import annotations

import re
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, event, select, update
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.orm import Session as SyncSession

from app.core.database import Base

_LOCALE_PATTERN = re.compile(r"^[a-z]{2,5}(?:-[a-z0-9]{2,8})?$")


def normalize_locale_code(locale: str | None) -> str | None:
    """Normalize locale code for coverage metrics.

    We standardize region variants to their base locale (for example, fr-CA -> fr)
    so availability reflects playable language families rather than country variants.
    """
    if not locale:
        return None

    raw = locale.strip().lower().replace("_", "-")
    if not raw or not _LOCALE_PATTERN.match(raw):
        return None

    return raw.split("-", 1)[0]


def _is_non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _extract_valid_category_locales(translations: dict[str, object] | None) -> set[str]:
    """Return normalized locales that have a valid category name."""
    valid: set[str] = set()
    for raw_locale, payload in (translations or {}).items():
        locale = normalize_locale_code(raw_locale)
        if not locale or not isinstance(payload, dict):
            continue
        name = payload.get("name")
        if _is_non_empty_string(name):
            valid.add(locale)
    return valid


def _extract_valid_prompt_locales(translations: dict[str, object] | None) -> set[str]:
    """Return normalized locales that have a valid prompt label payload."""
    valid: set[str] = set()
    for raw_locale, payload in (translations or {}).items():
        locale = normalize_locale_code(raw_locale)
        if not locale or not isinstance(payload, dict):
            continue

        label = payload.get("label")
        aliases = payload.get("aliases")
        aliases_valid = aliases is None or isinstance(aliases, list)
        if _is_non_empty_string(label) and aliases_valid:
            valid.add(locale)
    return valid


class Category(Base):
    """Language-neutral category concept."""

    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str | None] = mapped_column(String(100), nullable=True)
    difficulty: Mapped[str] = mapped_column(String(20), nullable=False)
    default_locale: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="system")

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


# --- Automatic Sync Logic ---


def _sync_category_locales(session: SyncSession, category_id: int) -> None:
    """Recompute category.available_locales for locales that are fully playable.

    A locale is considered available only when:
    - the category itself has a translation in that locale, and
    - every linked prompt has a translation in that locale.
    """
    # 1. Get category translations.
    cat_translations = session.scalar(select(Category.translations).where(Category.id == category_id))
    if not cat_translations:
        session.execute(update(Category).where(Category.id == category_id).values(available_locales=[]))
        return

    category_locales = _extract_valid_category_locales(cat_translations)
    if not category_locales:
        session.execute(update(Category).where(Category.id == category_id).values(available_locales=[]))
        return

    # 2. Get all linked prompt IDs.
    prompt_ids = session.scalars(
        select(CategoryPrompt.prompt_id).where(CategoryPrompt.category_id == category_id)
    ).all()

    if not prompt_ids:
        session.execute(update(Category).where(Category.id == category_id).values(available_locales=[]))
        return

    # 3. Build prompt translation coverage by locale.
    pt_result = session.execute(select(Prompt.id, Prompt.translations).where(Prompt.id.in_(prompt_ids))).all()

    locales_map: dict[str, set[int]] = {}
    for p_id, p_trans in pt_result:
        for normalized in _extract_valid_prompt_locales(p_trans):
            locales_map.setdefault(normalized, set()).add(p_id)

    num_prompts = len(prompt_ids)
    available = sorted(loc for loc in category_locales if len(locales_map.get(loc, set())) == num_prompts)

    # 4. Update Category.
    session.execute(update(Category).where(Category.id == category_id).values(available_locales=available))


@event.listens_for(SyncSession, "after_flush")
def update_category_locales_on_flush(session: SyncSession, flush_context: object) -> None:
    """Automatically maintain available_locales cache across DB inserts/updates."""
    dirty_cat_ids = set()

    for obj in session.new.union(session.dirty):
        if isinstance(obj, Category):
            if session.is_modified(obj, include_collections=True):
                dirty_cat_ids.add(obj.id)
        elif isinstance(obj, Prompt):
            if session.is_modified(obj, include_collections=True):
                linked = session.scalars(
                    select(CategoryPrompt.category_id).where(CategoryPrompt.prompt_id == obj.id)
                ).all()
                dirty_cat_ids.update(linked)
        elif isinstance(obj, CategoryPrompt):
            dirty_cat_ids.add(obj.category_id)

    for obj in session.deleted:
        if isinstance(obj, CategoryPrompt):
            dirty_cat_ids.add(obj.category_id)

    for cid in dirty_cat_ids:
        if cid:
            _sync_category_locales(session, cid)
