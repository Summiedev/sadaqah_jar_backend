"""add note to sadaqah_logs

Revision ID: 0005_add_note_to_sadaqah_logs
Revises: 46f27cb272c5
Create Date: 2026-07-21 14:56:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0005_add_note_to_sadaqah_logs"
down_revision: Union[str, Sequence[str], None] = "46f27cb272c5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sadaqah_logs", sa.Column("note", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("sadaqah_logs", "note")
