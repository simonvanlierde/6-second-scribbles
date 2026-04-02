"""Add room_id and created_by to categories for custom categories

Revision ID: 001
Revises:
Create Date: 2025-01-18 14:30:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Drop unique constraint on name (if it exists)
    # This allows multiple rooms to have categories with the same name
    try:
        op.drop_constraint('categories_name_key', 'categories', type_='unique')
    except:
        pass  # Constraint might not exist yet

    # Add room_id column (nullable, for room-specific categories)
    op.add_column('categories', sa.Column('room_id', sa.String(length=10), nullable=True))

    # Add created_by column (nullable, stores player ID who created custom category)
    op.add_column('categories', sa.Column('created_by', sa.String(length=50), nullable=True))

    # Create index on room_id for efficient queries
    op.create_index('idx_category_room', 'categories', ['room_id'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_category_room', table_name='categories')

    # Remove columns
    op.drop_column('categories', 'created_by')
    op.drop_column('categories', 'room_id')

    # Restore unique constraint on name
    op.create_unique_constraint('categories_name_key', 'categories', ['name'])
