"""hash password-reset and email-verification credentials

Revision ID: 0002_hash_one_time_auth_tokens
Revises: 0001_initial_users
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "0002_hash_one_time_auth_tokens"
down_revision: Union[str, Sequence[str], None] = "0001_initial_users"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_raw_token_column(table: str) -> None:
    # One-time credentials are intentionally invalidated. Existing values were
    # stored in plaintext and cannot be safely converted without preserving
    # their secret material during migration.
    op.execute(sa.text(f"DELETE FROM {table}"))
    with op.batch_alter_table(table) as batch:
        batch.drop_index(f"ix_{table}_token")
        batch.drop_column("token")
        batch.add_column(sa.Column("token_hash", sa.String(length=64), nullable=False))
        batch.create_unique_constraint(f"uq_{table}_token_hash", ["token_hash"])
        batch.create_index(f"ix_{table}_token_hash", ["token_hash"], unique=False)


def upgrade() -> None:
    _replace_raw_token_column("email_verification_tokens")
    _replace_raw_token_column("password_reset_tokens")


def downgrade() -> None:
    for table in ("password_reset_tokens", "email_verification_tokens"):
        with op.batch_alter_table(table) as batch:
            batch.drop_index(f"ix_{table}_token_hash")
            batch.drop_constraint(f"uq_{table}_token_hash", type_="unique")
            batch.drop_column("token_hash")
            batch.add_column(sa.Column("token", sa.String(length=64), nullable=False))
            batch.create_unique_constraint(f"uq_{table}_token", ["token"])
            batch.create_index(f"ix_{table}_token", ["token"], unique=False)
