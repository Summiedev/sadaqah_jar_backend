"""add targeted family invitation recipients

Revision ID: c7d8e9f0a1b2
Revises: b40d9d5fddae, 7c3b2a1f9e4d
Create Date: 2026-08-21 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, Sequence[str], None] = (
    "b40d9d5fddae",
    "7c3b2a1f9e4d",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "family_invitations",
        sa.Column("invited_user_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "family_invitations",
        sa.Column("invited_email", sa.String(length=320), nullable=True),
    )
    op.create_foreign_key(
        "fk_family_invitations_invited_user_id_users",
        "family_invitations",
        "users",
        ["invited_user_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_family_invitations_invited_user_id",
        "family_invitations",
        ["invited_user_id"],
    )
    op.create_index(
        "ix_family_invitations_invited_email",
        "family_invitations",
        ["invited_email"],
    )
    op.create_index(
        "ix_family_invitations_recipient_status",
        "family_invitations",
        ["invited_user_id", "status"],
    )
    op.create_index(
        "ix_family_invitations_email_status",
        "family_invitations",
        ["invited_email", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_family_invitations_email_status", table_name="family_invitations")
    op.drop_index("ix_family_invitations_recipient_status", table_name="family_invitations")
    op.drop_index("ix_family_invitations_invited_email", table_name="family_invitations")
    op.drop_index("ix_family_invitations_invited_user_id", table_name="family_invitations")
    op.drop_constraint(
        "fk_family_invitations_invited_user_id_users",
        "family_invitations",
        type_="foreignkey",
    )
    op.drop_column("family_invitations", "invited_email")
    op.drop_column("family_invitations", "invited_user_id")
