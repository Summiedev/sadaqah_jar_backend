"""add family jar log request id and response snapshot columns

Revision ID: f6a7b8c9d0e1
Revises: f5a6b7c8d9e0
Create Date: 2026-06-18 15:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "family_jar_logs",
        sa.Column("request_id", sa.String(length=36), nullable=True, index=True),
    )
    op.add_column(
        "family_jar_logs",
        sa.Column("response_current_stars", sa.Integer(), nullable=True),
    )
    op.add_column(
        "family_jar_logs",
        sa.Column("response_capacity", sa.Integer(), nullable=True),
    )
    op.add_column(
        "family_jar_logs",
        sa.Column("response_completed_at", sa.DateTime(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_family_jar_log_request",
        "family_jar_logs",
        ["user_id", "request_id"],
    )
    op.create_index(
        "ix_family_jar_log_user_date",
        "family_jar_logs",
        ["user_id", "date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_family_jar_log_user_date", table_name="family_jar_logs")
    op.drop_constraint("uq_family_jar_log_request", "family_jar_logs", type_="unique")
    op.drop_column("family_jar_logs", "response_completed_at")
    op.drop_column("family_jar_logs", "response_capacity")
    op.drop_column("family_jar_logs", "response_current_stars")
    op.drop_column("family_jar_logs", "request_id")