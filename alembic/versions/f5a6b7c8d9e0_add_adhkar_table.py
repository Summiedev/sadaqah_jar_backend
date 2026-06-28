"""add adhkar table

Revision ID: f5a6b7c8d9e0
Revises: e1f2a3b4c5d6
Create Date: 2026-06-18 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "adhkar",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_arabic", sa.Text(), nullable=False),
        sa.Column("text_translation", sa.Text(), nullable=False),
        sa.Column(
            "time_of_day",
            sa.Enum("morning", "evening", name="timeofday", native_enum=False),
            nullable=False,
        ),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("repeat_count", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_adhkar_time_of_day"),
        "adhkar",
        ["time_of_day"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_adhkar_time_of_day"), table_name="adhkar")
    op.drop_table("adhkar")
    op.execute("DROP TYPE IF EXISTS timeofday")