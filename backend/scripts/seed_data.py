"""Seed script to load card deck data into the database.

Run this after setting up the database:
    python scripts/seed_data.py
"""

import asyncio
import json
import logging
from pathlib import Path

from sqlalchemy import delete, select

from app.categories.models import Card, Category
from app.core.database import get_session_maker, init_db
from app.core.logging import configure_logging

configure_logging()
logger = logging.getLogger(__name__)

CARD_DECKS = json.loads((Path(__file__).parent / "seed_data.json").read_text())
CLEAR_FLAG = "--clear"


async def seed_database() -> None:
    """Seed the database with card deck data."""
    await init_db()

    async with get_session_maker()() as session:
        try:
            result = await session.execute(select(Category))
            existing = result.scalars().all()

            if existing:
                return

            total_categories = 0
            total_items = 0

            for difficulty, categories in CARD_DECKS.items():
                for cat_data in categories:
                    category = Category(
                        name=cat_data["category"],
                        difficulty=difficulty,
                        language=cat_data.get("language", "en"),
                        description=f"{difficulty.capitalize()} difficulty category",
                    )
                    session.add(category)
                    await session.flush()

                    for item in cat_data["items"]:
                        card = Card(
                            category_id=category.id,
                            item=item,
                            alternatives=[],
                        )
                        session.add(card)

                    total_categories += 1
                    total_items += len(cat_data["items"])

            await session.commit()

        except Exception:
            await session.rollback()
            raise


async def clear_database() -> None:
    """Clear all data from the database (use with caution!)."""
    async with get_session_maker()() as session:
        try:
            await session.execute(delete(Category))
            await session.commit()
        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == CLEAR_FLAG:
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())
