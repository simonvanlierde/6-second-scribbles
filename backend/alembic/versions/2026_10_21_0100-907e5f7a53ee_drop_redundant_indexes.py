"""Drop redundant and unused indexes

Revision ID: 907e5f7a53ee
Revises: b2a7f484d1a9
Create Date: 2026-10-21 01:00:00

"""

from typing import TYPE_CHECKING

from alembic import op

if TYPE_CHECKING:
    from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "907e5f7a53ee"
down_revision: str | None = "b2a7f484d1a9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (index, table, columns, unique, using). The unique constraints users_username_key and
# prompts_stable_key_key, and uq_category_prompt (category_id, prompt_id), already index
# the first three; no query filters on the other three columns.
_INDEXES: list[tuple[str, str, list[str], bool, str | None]] = [
    ("idx_users_username", "users", ["username"], True, None),
    ("idx_prompt_stable_key", "prompts", ["stable_key"], False, None),
    ("idx_category_prompt_category", "category_prompts", ["category_id"], False, None),
    ("idx_users_preferred_locale", "users", ["preferred_locale"], False, None),
    ("idx_category_translations", "categories", ["translations"], False, "gin"),
    ("idx_prompt_translations", "prompts", ["translations"], False, "gin"),
]


def upgrade() -> None:
    # CONCURRENTLY cannot run inside a transaction. The session's lock_timeout and
    # statement_timeout from env.py still apply: SET lasts for the whole connection.
    with op.get_context().autocommit_block():
        for name, table, _, _, _ in _INDEXES:
            op.drop_index(name, table_name=table, postgresql_concurrently=True, if_exists=True)


def downgrade() -> None:
    with op.get_context().autocommit_block():
        for name, table, columns, unique, using in _INDEXES:
            op.create_index(
                name,
                table,
                columns,
                unique=unique,
                postgresql_using=using,
                postgresql_concurrently=True,
                if_not_exists=True,
            )
