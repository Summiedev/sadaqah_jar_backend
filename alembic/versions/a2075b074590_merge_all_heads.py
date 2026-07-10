"""merge_all_heads

Revision ID: a2075b074590
Revises: c4a2d4b1e8f7, d7e8f9a0b1c2, e7f8a9b0c1d2, f6a7b8c9d0e1
Create Date: 2026-06-28 13:24:20.940299

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a2075b074590'
down_revision: Union[str, Sequence[str], None] = ('c4a2d4b1e8f7', 'd7e8f9a0b1c2', 'e7f8a9b0c1d2', 'f6a7b8c9d0e1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
