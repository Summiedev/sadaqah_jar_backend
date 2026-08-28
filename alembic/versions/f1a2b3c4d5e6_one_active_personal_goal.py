"""enforce one active personal goal per user."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older installations may contain multiple active rows. Preserve the
    # newest goal and keep the others in history before adding the constraint.
    op.execute(
        sa.text(
            """
            UPDATE user_goals AS older
            SET status = 'archived', updated_at = CURRENT_TIMESTAMP
            WHERE older.status = 'active'
              AND older.deleted_at IS NULL
              AND EXISTS (
                SELECT 1
                FROM user_goals AS newer
                WHERE newer.user_id = older.user_id
                  AND newer.status = 'active'
                  AND newer.deleted_at IS NULL
                  AND (
                    newer.created_at > older.created_at
                    OR (newer.created_at = older.created_at AND newer.id > older.id)
                  )
              )
            """
        )
    )
    op.create_index(
        "uq_user_goals_one_active",
        "user_goals",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND deleted_at IS NULL"),
        sqlite_where=sa.text("status = 'active' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_user_goals_one_active", table_name="user_goals")
