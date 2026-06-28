"""add user avatar data

Revision ID: c4a2d4b1e8f7
Revises: 8a4d7e1b9c2f
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c4a2d4b1e8f7"
down_revision: Union[str, Sequence[str], None] = "8a4d7e1b9c2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_data", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_data")