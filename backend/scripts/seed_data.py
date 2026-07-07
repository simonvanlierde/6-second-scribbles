"""Seed script to load category data into the database (M2M + Library-First YAML).

Run this from the backend directory after setting up the database:
    uv run python -m scripts.seed_data              # seed a fresh DB; warn + abort if already seeded
    uv run python -m scripts.seed_data --append     # add only categories not already present
    uv run python -m scripts.seed_data --overwrite  # replace all system categories + prompts
    uv run python -m scripts.seed_data --clear       # delete ALL categories, prompts, and users
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml
from sqlalchemy import delete, select

from app.categories.models import (
    DEFAULT_CATEGORY_SOURCE,
    Category,
    CategoryPrompt,
    Prompt,
    compute_available_locales,
    normalize_locale_code,
)
from app.core.database import get_session_maker
from app.core.logging import configure_logging
from app.users.models import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).parent / "seed_data.yaml"
SEED_DATA = yaml.safe_load(SEED_DATA_PATH.read_text())

SEEDED_USERS_KEY = "seeded_users"
SYSTEM_CATEGORIES_KEY = "system_categories"
PROMPTS_KEY = "prompts"


def _build_prompt_translations(translations: list[dict[str, Any]]) -> dict[str, object]:
    """Normalize prompt translations into the persisted dict shape."""
    return {
        normalize_locale_code(str(t_data["locale"])) or str(t_data["locale"]): {
            "label": str(t_data["label"]),
            "aliases": [str(alias) for alias in (t_data.get("aliases") or [])],
        }
        for t_data in translations
    }


def _build_category_translations(translations: list[dict[str, Any]]) -> dict[str, object]:
    """Normalize category translations into the persisted dict shape."""
    return {
        normalize_locale_code(str(t_data["locale"])) or str(t_data["locale"]): {"name": str(t_data["name"])}
        for t_data in translations
    }


async def _seed_prompt_library(session: AsyncSession, prompts_data: list[dict[str, Any]]) -> None:
    """Populate the global prompt library."""
    for p_data in prompts_data:
        stable_key = str(p_data["id"])

        # Get or create Prompt
        result = await session.execute(select(Prompt).where(Prompt.stable_key == stable_key))
        prompt = result.scalar_one_or_none()

        if not prompt:
            prompt = Prompt(
                stable_key=stable_key,
                translations=_build_prompt_translations(list(p_data["translations"])),
            )
            session.add(prompt)
    await session.flush()


async def _create_category(
    session: AsyncSession,
    *,
    id_name: str,
    difficulty: str,
    default_locale: str,
    translations: list[dict[str, Any]],
    items: list[str],
) -> tuple[Category, int]:
    translations_dict = _build_category_translations(translations)

    # Resolve linked prompts up front so we can compute available_locales
    # explicitly at insert time (the old SQLAlchemy after_flush listener is gone).
    resolved_prompts: list[tuple[int, Prompt]] = []
    for index, stable_key in enumerate(items, start=1):
        result = await session.execute(select(Prompt).where(Prompt.stable_key == stable_key))
        prompt = result.scalar_one_or_none()
        if not prompt:
            logger.warning(
                "Prompt '%s' referenced in category '%s' not found in library; skipping.", stable_key, id_name
            )
            continue
        resolved_prompts.append((index, prompt))

    available_locales = compute_available_locales(
        translations_dict,
        [p.translations for _, p in resolved_prompts],
    )
    if not available_locales:
        logger.warning("Category '%s' has no fully playable locales; it will be skipped by selection queries.", id_name)

    category = Category(
        slug=id_name,
        difficulty=difficulty.lower(),
        default_locale=default_locale,
        source="system",
        translations=translations_dict,
        available_locales=available_locales,
    )
    session.add(category)
    await session.flush()

    for index, prompt in resolved_prompts:
        session.add(
            CategoryPrompt(
                category_id=category.id,
                prompt_id=prompt.id,
                sort_order=index,
            )
        )

    await session.flush()
    return category, len(resolved_prompts)


async def seed_database(*, overwrite: bool = False, append: bool = False) -> None:
    """Seed the database using M2M + Library-First logic.

    Modes (mutually exclusive):
      - default: seed a fresh database. If system categories already exist, warn
        and make no changes — the caller must opt in via ``overwrite`` or ``append``.
      - ``overwrite``: delete existing system categories and the prompt library,
        then re-seed everything from the YAML.
      - ``append``: leave existing data untouched; insert only categories whose
        slug is not already present (the prompt library is get-or-create either way).
    """
    async with get_session_maker()() as session:
        try:
            existing_slugs = set(
                (await session.execute(select(Category.slug).where(Category.source == DEFAULT_CATEGORY_SOURCE)))
                .scalars()
                .all()
            )

            if existing_slugs and not (overwrite or append):
                logger.warning(
                    "Database already contains %d system categories; making no changes. "
                    "Re-run with --append to add only new entries, or --overwrite to replace all system data.",
                    len(existing_slugs),
                )
                return

            if overwrite:
                logger.info(
                    "Overwrite mode: clearing %d existing system categories and the prompt library.",
                    len(existing_slugs),
                )
                await session.execute(delete(Category).where(Category.source == DEFAULT_CATEGORY_SOURCE))
                await session.execute(delete(Prompt))
                existing_slugs = set()
            elif existing_slugs:
                logger.info("Append mode: %d existing system categories will be left untouched.", len(existing_slugs))

            # 1. Seed Prompt Library (get-or-create; safe to run in append mode)
            prompts = SEED_DATA.get(PROMPTS_KEY, [])
            await _seed_prompt_library(session, prompts)
            logger.info("Populated Prompt Library with %d entries.", len(prompts))

            # 2. Seed Categories, skipping any slug that already exists (append mode)
            total_categories = 0
            total_links = 0
            skipped = 0
            for cat_data in SEED_DATA.get(SYSTEM_CATEGORIES_KEY, []):
                slug = str(cat_data["id"])
                if slug in existing_slugs:
                    skipped += 1
                    continue
                _, created_links = await _create_category(
                    session,
                    id_name=slug,
                    difficulty=str(cat_data["difficulty"]),
                    default_locale=str(cat_data.get("default_locale", "en")),
                    translations=list(cat_data["translations"]),
                    items=list(cat_data["items"]),
                )
                total_categories += 1
                total_links += created_links

            await session.commit()
            logger.info(
                "Seeded database with %d new categories and %d prompt links (skipped %d existing).",
                total_categories,
                total_links,
                skipped,
            )

        except Exception:
            await session.rollback()
            raise


async def clear_database() -> None:
    """Clear all data from the database. Use with caution!"""
    async with get_session_maker()() as session:
        try:
            logger.info("Clearing database")
            await session.execute(delete(Category))
            await session.execute(delete(Prompt))
            await session.execute(delete(User))
            await session.commit()
            logger.info("Database cleared")
        except Exception:
            await session.rollback()
            raise


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed category data into the database.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--overwrite",
        action="store_true",
        help="Delete existing system categories and the prompt library, then re-seed from scratch.",
    )
    group.add_argument(
        "--append",
        action="store_true",
        help="Insert only categories whose slug is not already present; leave existing data untouched.",
    )
    group.add_argument(
        "--clear",
        action="store_true",
        help="Delete ALL categories, prompts, and users. Use with caution.",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    configure_logging()
    args = _parse_args(sys.argv[1:])
    if args.clear:
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database(overwrite=args.overwrite, append=args.append))
