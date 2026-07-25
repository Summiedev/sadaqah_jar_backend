"""create sadaqah activities domain

Revision ID: 46f27cb272c5
Revises: 0004_notification_enhancements
Create Date: 2026-07-20 17:27:29.735850

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "46f27cb272c5"
down_revision: Union[str, Sequence[str], None] = "0004_notification_enhancements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "activity_completions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("context", sa.String(32), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.Column("stars_earned", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("friday_boost", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("ramadan_bonus", sa.Boolean(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["family.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_completions_user_date", "activity_completions", ["user_id", "completed_at"])
    op.create_index("ix_activity_completions_user_type", "activity_completions", ["user_id", "activity_type"])
    op.create_index("ix_activity_completions_family", "activity_completions", ["family_id", "completed_at"])

    op.create_table(
        "activity_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("ended_at", sa.DateTime(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("context", sa.String(32), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["family_id"], ["family.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_activity_sessions_user_started", "activity_sessions", ["user_id", "started_at"])

    op.create_table(
        "activity_streaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("activity_type", sa.String(32), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "activity_type", name="uq_activity_streak"),
    )


def downgrade() -> None:
    op.drop_table("activity_streaks")
    op.drop_table("activity_sessions")
    op.drop_index("ix_activity_completions_family", table_name="activity_completions")
    op.drop_index("ix_activity_completions_user_type", table_name="activity_completions")
    op.drop_index("ix_activity_completions_user_date", table_name="activity_completions")
    op.drop_table("activity_completions")
