"""merge migration heads

Revision ID: b40d9d5fddae
Revises: 69286f7ad8b8, f4c2a9d8e7b1
Create Date: 2026-08-08 20:39:19.419172

"""

from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "b40d9d5fddae"
down_revision: Union[str, Sequence[str], None] = ("69286f7ad8b8", "f4c2a9d8e7b1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
