"""Add language support to categories

Revision ID: 002
Revises: 001
Create Date: 2025-01-18 19:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add language column with default value 'en' (English)
    # This uses ISO 639-1 language codes: en (English), es (Spanish), fr (French), etc.
    op.add_column('categories', sa.Column('language', sa.String(length=5), nullable=False, server_default='en'))

    # Create index on language for efficient filtering
    op.create_index('idx_category_language', 'categories', ['language'], unique=False)


def downgrade() -> None:
    # Remove index
    op.drop_index('idx_category_language', table_name='categories')

    # Remove column
    op.drop_column('categories', 'language')
