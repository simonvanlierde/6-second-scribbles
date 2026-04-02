"""Drop game_sessions table

Revision ID: 003
Revises: 002
Create Date: 2026-03-28 00:01:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_session_room", table_name="game_sessions")
    op.drop_index("idx_session_started", table_name="game_sessions")
    op.drop_table("game_sessions")


def downgrade() -> None:
    op.create_table(
        "game_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("room_code", sa.String(length=10), nullable=False),
        sa.Column("player_count", sa.Integer(), nullable=False),
        sa.Column("difficulty", sa.String(length=20), nullable=False),
        sa.Column("rounds", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("final_scores", sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_session_room", "game_sessions", ["room_code"])
    op.create_index("idx_session_started", "game_sessions", ["started_at"])
