"""add family jar streak columns

Revision ID: d1e2f3a4b5c6
Revises: c2d3e4f5g6h7
Create Date: 2026-06-18 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5g6h7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("family_jars", sa.Column("last_activity_date", sa.Date(), nullable=True))
    op.add_column(
        "family_jars",
        sa.Column("streak_days", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )
    op.add_column(
        "family_jars",
        sa.Column("longest_streak", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_column("family_jars", "longest_streak")
    op.drop_column("family_jars", "streak_days")
    op.drop_column("family_jars", "last_activity_date")
