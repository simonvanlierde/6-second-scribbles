"""Fix schema: timezone-aware datetimes, room_id length, drop duplicate indexes.

Revision ID: 004
Revises: 003
Create Date: 2026-04-01 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Make all datetime columns timezone-aware
    op.alter_column(
        "categories",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "categories",
        "updated_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )
    op.alter_column(
        "cards",
        "created_at",
        type_=sa.DateTime(timezone=True),
        existing_type=sa.DateTime(),
        existing_nullable=True,
    )

    # Widen room_id from VARCHAR(10) to VARCHAR(50)
    op.alter_column(
        "categories",
        "room_id",
        type_=sa.String(50),
        existing_type=sa.String(10),
        existing_nullable=True,
    )

    # Drop duplicate column-level indexes (the explicit __table_args__ ones remain)
    op.drop_index("ix_categories_difficulty", table_name="categories", if_exists=True)
    op.drop_index("ix_categories_language", table_name="categories", if_exists=True)
    op.drop_index("ix_categories_name", table_name="categories", if_exists=True)
    op.drop_index("ix_categories_room_id", table_name="categories", if_exists=True)


def downgrade() -> None:
    op.alter_column(
        "categories",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "categories",
        "updated_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "cards",
        "created_at",
        type_=sa.DateTime(),
        existing_type=sa.DateTime(timezone=True),
        existing_nullable=True,
    )
    op.alter_column(
        "categories",
        "room_id",
        type_=sa.String(10),
        existing_type=sa.String(50),
        existing_nullable=True,
    )
    op.create_index("ix_categories_difficulty", "categories", ["difficulty"])
    op.create_index("ix_categories_language", "categories", ["language"])
    op.create_index("ix_categories_name", "categories", ["name"])
    op.create_index("ix_categories_room_id", "categories", ["room_id"])
