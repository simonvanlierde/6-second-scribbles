"""Seed script to load category data into the database (M2M + Library-First YAML).

Run this after setting up the database:
    python scripts/seed_data.py
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import delete, select

from app.categories.models import (
    Category,
    CategoryPrompt,
    Prompt,
)
from app.core.database import get_session_maker
from app.core.logging import configure_logging
from app.users.models import User

configure_logging()
logger = logging.getLogger(__name__)

SEED_DATA_PATH = Path(__file__).parent / "seed_data.yaml"
SEED_DATA = yaml.safe_load(SEED_DATA_PATH.read_text())

CLEAR_FLAG = "--clear"
SEEDED_USERS_KEY = "seeded_users"
SYSTEM_CATEGORIES_KEY = "system_categories"
PROMPTS_KEY = "prompts"


def _iter_prompts(seed_data: dict[str, Any]) -> list[dict[str, Any]]:
    return seed_data.get(PROMPTS_KEY, [])


def _iter_system_categories(seed_data: dict[str, Any]) -> list[dict[str, Any]]:
    return seed_data.get(SYSTEM_CATEGORIES_KEY, [])


async def _seed_prompt_library(session, prompts_data: list[dict[str, Any]]):
    """Populate the global prompt library."""
    for p_data in prompts_data:
        stable_key = str(p_data["id"])

        # Get or create Prompt
        result = await session.execute(select(Prompt).where(Prompt.stable_key == stable_key))
        prompt = result.scalar_one_or_none()

        if not prompt:
            translations_dict = {}
            for t_data in p_data["translations"]:
                translations_dict[str(t_data["locale"]).lower()] = {
                    "label": str(t_data["label"]),
                    "aliases": [str(alias) for alias in (t_data.get("aliases") or [])],
                }

            prompt = Prompt(stable_key=stable_key, translations=translations_dict)
            session.add(prompt)
    await session.flush()


async def _create_category(
    session,
    *,
    id_name: str,
    difficulty: str,
    default_locale: str,
    translations: list[dict[str, Any]],
    items: list[str],
) -> tuple[Category, int]:
    translations_dict = {}
    for t_data in translations:
        translations_dict[str(t_data["locale"]).lower()] = {"name": str(t_data["name"])}

    category = Category(
        slug=id_name,
        difficulty=difficulty.lower(),
        default_locale=default_locale,
        source="system",
        translations=translations_dict,
    )
    session.add(category)
    await session.flush()

    links_created = 0
    for index, stable_key in enumerate(items, start=1):
        # Lookup Prompt
        result = await session.execute(select(Prompt).where(Prompt.stable_key == stable_key))
        prompt = result.scalar_one_or_none()

        if not prompt:
            logger.warning(f"Prompt '{stable_key}' referenced in category '{id_name}' not found in library; skipping.")
            continue

        session.add(
            CategoryPrompt(
                category_id=category.id,
                prompt_id=prompt.id,
                sort_order=index,
            )
        )
        links_created += 1

    await session.flush()
    return category, links_created


async def seed_database() -> None:
    """Seed the database using M2M + Library-First logic."""
    async with get_session_maker()() as session:
        try:
            logger.info("Starting database seed")
            # Clear existing system data for a clean re-seed
            await session.execute(delete(Category).where(Category.source == "system"))
            await session.execute(delete(Prompt))

            # 1. Seed Prompt Library
            prompts = _iter_prompts(SEED_DATA)
            await _seed_prompt_library(session, prompts)
            logger.info(f"Populated Prompt Library with {len(prompts)} entries.")

            # 2. Seed Categories
            total_categories = 0
            total_links = 0
            for cat_data in _iter_system_categories(SEED_DATA):
                _, created_links = await _create_category(
                    session,
                    id_name=str(cat_data["id"]),
                    difficulty=str(cat_data["difficulty"]),
                    default_locale=str(cat_data.get("default_locale", "en")),
                    translations=list(cat_data["translations"]),
                    items=list(cat_data["items"]),
                )
                total_categories += 1
                total_links += created_links

            await session.commit()
            logger.info(
                "Seeded database with %s categories and %s prompt links (Many-to-Many).",
                total_categories,
                total_links,
            )

        except Exception:
            await session.rollback()
            raise


async def clear_database() -> None:
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


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == CLEAR_FLAG:
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())
