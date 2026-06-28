"""add new categories and estimated_time_minutes to sadaqah_acts

Revision ID: c6e1f8a3d0b2
Revises: 8a4d7e1b9c2f
Create Date: 2026-06-17 23:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c6e1f8a3d0b2"
down_revision: Union[str, Sequence[str], None] = "8a4d7e1b9c2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


old_options = ("general", "dhikr", "community", "donation")
new_options = ("general", "dhikr", "community", "donation", "kindness", "family", "knowledge", "environment", "character")


def upgrade() -> None:
    op.add_column(
        "sadaqah_acts",
        sa.Column("estimated_time_minutes", sa.Integer(), nullable=True),
    )
    with op.batch_alter_table("sadaqah_acts") as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.Enum(*old_options, name="sadaqahcategory", native_enum=False),
            type_=sa.Enum(*new_options, name="sadaqahcategory", native_enum=False),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("sadaqah_acts") as batch_op:
        batch_op.alter_column(
            "category",
            existing_type=sa.Enum(*new_options, name="sadaqahcategory", native_enum=False),
            type_=sa.Enum(*old_options, name="sadaqahcategory", native_enum=False),
            existing_nullable=False,
        )
    op.drop_column("sadaqah_acts", "estimated_time_minutes")