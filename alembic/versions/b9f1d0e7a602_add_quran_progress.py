"""add quran progress

Revision ID: b9f1d0e7a602
Revises: a8f4d2b6c901
Create Date: 2026-08-07 19:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b9f1d0e7a602"
down_revision: Union[str, Sequence[str], None] = "a8f4d2b6c901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journey_quran_progress",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("surah_id", sa.Integer(), nullable=False),
        sa.Column("verse_key", sa.String(length=16), nullable=False),
        sa.Column("page", sa.Integer(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_journey_quran_progress_user"),
    )
    op.create_index(
        op.f("ix_journey_quran_progress_id"),
        "journey_quran_progress",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journey_quran_progress_last_read_at"),
        "journey_quran_progress",
        ["last_read_at"],
        unique=False,
    )
    op.create_index(
        op.f("ix_journey_quran_progress_user_id"),
        "journey_quran_progress",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_journey_quran_progress_user_id"),
        table_name="journey_quran_progress",
    )
    op.drop_index(
        op.f("ix_journey_quran_progress_last_read_at"),
        table_name="journey_quran_progress",
    )
    op.drop_index(
        op.f("ix_journey_quran_progress_id"),
        table_name="journey_quran_progress",
    )
    op.drop_table("journey_quran_progress")
