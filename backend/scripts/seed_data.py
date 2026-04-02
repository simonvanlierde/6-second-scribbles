"""Seed script to load card deck data into the database.

Run this after setting up the database:
    python scripts/seed_data.py
"""

import asyncio
import json
from pathlib import Path

from sqlalchemy import delete, select

from app.database import get_session_maker, init_db
from app.db_models import Card, Category

CARD_DECKS = json.loads((Path(__file__).parent / "seed_data.json").read_text())


async def seed_database() -> None:
    """Seed the database with card deck data."""
    print("🌱 Starting database seed...")

    await init_db()
    print("✅ Database tables initialized")

    async with get_session_maker()() as session:
        try:
            result = await session.execute(select(Category))
            existing = result.scalars().all()

            if existing:
                print("⚠️  Database already contains data. Skipping seed.")
                print(f"   Found {len(existing)} categories")
                return

            total_categories = 0
            total_items = 0

            for difficulty, categories in CARD_DECKS.items():
                print(f"\n📦 Seeding {difficulty} categories...")

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

                    print(f"   ✓ {cat_data['category']} ({len(cat_data['items'])} items)")

            await session.commit()

            print("\n✅ Seed complete!")
            print(f"   📊 {total_categories} categories created")
            print(f"   📝 {total_items} items added")

        except Exception as e:
            await session.rollback()
            print(f"\n❌ Error seeding database: {e}")
            raise


async def clear_database() -> None:
    """Clear all data from the database (use with caution!)."""
    print("⚠️  Clearing database...")

    async with get_session_maker()() as session:
        try:
            await session.execute(delete(Category))
            await session.commit()
            print("✅ Database cleared")
        except Exception as e:
            await session.rollback()
            print(f"❌ Error clearing database: {e}")
            raise


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        asyncio.run(clear_database())
    else:
        asyncio.run(seed_database())
