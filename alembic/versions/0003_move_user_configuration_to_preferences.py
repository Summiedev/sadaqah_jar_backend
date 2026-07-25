"""move user configuration to the Users preference aggregate

Revision ID: 0003_move_user_configuration_to_preferences
Revises: 0002_hash_one_time_auth_tokens
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_move_user_configuration_to_preferences"
down_revision: Union[str, Sequence[str], None] = "0002_hash_one_time_auth_tokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.add_column(sa.Column("timezone", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("selected_mode", sa.String(length=20), nullable=False, server_default="BOTH"))
    op.execute("UPDATE user_preferences SET timezone = (SELECT timezone FROM users WHERE users.id = user_preferences.user_id)")
    op.execute("UPDATE user_preferences SET selected_mode = COALESCE((SELECT mode FROM users WHERE users.id = user_preferences.user_id), 'BOTH')")
    with op.batch_alter_table("users") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")))
        batch.drop_column("mode")
        batch.drop_column("timezone")
        batch.drop_column("locale")
    with op.batch_alter_table("user_devices") as batch:
        batch.add_column(sa.Column("app_version", sa.String(length=32), nullable=True))


def downgrade() -> None:
    raise NotImplementedError("User configuration migration is intentionally irreversible")
