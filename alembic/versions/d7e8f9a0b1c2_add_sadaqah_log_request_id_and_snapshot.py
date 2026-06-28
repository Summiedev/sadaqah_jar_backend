"""add sadaqah log request id and response snapshot

Revision ID: d7e8f9a0b1c2
Revises: b1c2d3e4f5g6
Create Date: 2026-06-18 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7e8f9a0b1c2"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5g6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sadaqah_logs", sa.Column("request_id", sa.String(length=36), nullable=True))
    op.add_column("sadaqah_logs", sa.Column("response_current_stars", sa.Integer(), nullable=True))
    op.add_column("sadaqah_logs", sa.Column("response_capacity", sa.Integer(), nullable=True))
    op.add_column("sadaqah_logs", sa.Column("response_completed_at", sa.DateTime(), nullable=True))
    op.create_unique_constraint(
        "unique_sadaqah_log_request",
        "sadaqah_logs",
        ["user_id", "request_id"],
    )


def downgrade() -> None:
    op.drop_constraint("unique_sadaqah_log_request", "sadaqah_logs", type_="unique")
    op.drop_column("sadaqah_logs", "response_completed_at")
    op.drop_column("sadaqah_logs", "response_capacity")
    op.drop_column("sadaqah_logs", "response_current_stars")
    op.drop_column("sadaqah_logs", "request_id")
