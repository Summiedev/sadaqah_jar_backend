"""add composite index on jars (user_id, completed_at)

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-06-17 23:30:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_jars_user_id_completed_at",
        "jars",
        ["user_id", "completed_at"],
        unique=False,
        postgresql_where=op.text("completed_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_jars_user_id_completed_at", table_name="jars")