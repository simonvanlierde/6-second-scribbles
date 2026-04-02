"""Create the current application schema.

Revision ID: 001
Revises:
Create Date: 2026-04-02 00:01:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("language", sa.String(length=5), nullable=False),
        sa.Column("room_id", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_category_difficulty", "categories", ["difficulty"], unique=False)
    op.create_index("idx_category_language", "categories", ["language"], unique=False)
    op.create_index("idx_category_name", "categories", ["name"], unique=False)
    op.create_index("idx_category_room", "categories", ["room_id"], unique=False)

    op.create_table(
        "cards",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("item", sa.String(length=100), nullable=False),
        sa.Column("alternatives", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_card_category", "cards", ["category_id"], unique=False)
    op.create_index("idx_card_item", "cards", ["item"], unique=False)


def downgrade() -> None:
    op.drop_index("idx_card_item", table_name="cards")
    op.drop_index("idx_card_category", table_name="cards")
    op.drop_table("cards")

    op.drop_index("idx_category_room", table_name="categories")
    op.drop_index("idx_category_name", table_name="categories")
    op.drop_index("idx_category_language", table_name="categories")
    op.drop_index("idx_category_difficulty", table_name="categories")
    op.drop_table("categories")
