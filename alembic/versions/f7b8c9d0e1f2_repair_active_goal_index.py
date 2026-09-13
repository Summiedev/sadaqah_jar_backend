"""repair the one-active-goal index for SQLAlchemy enum storage."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Older deployments may already have the predicate from f1...; remove it
    # before rebuilding the index with the value actually stored by
    # sa.Enum(GoalStatus, native_enum=False).
    op.drop_index("uq_user_goals_one_active", table_name="user_goals")
    op.execute(
        sa.text(
            """
            UPDATE user_goals
            SET status = UPPER(status), updated_at = CURRENT_TIMESTAMP
            WHERE status IN ('active', 'completed', 'archived', 'replaced')
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE user_goals AS older
            SET status = 'ARCHIVED', updated_at = CURRENT_TIMESTAMP
            WHERE older.status = 'ACTIVE'
              AND older.deleted_at IS NULL
              AND EXISTS (
                SELECT 1
                FROM user_goals AS newer
                WHERE newer.user_id = older.user_id
                  AND newer.status = 'ACTIVE'
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
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
        sqlite_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_user_goals_one_active", table_name="user_goals")
    op.create_index(
        "uq_user_goals_one_active",
        "user_goals",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
        sqlite_where=sa.text("status = 'ACTIVE' AND deleted_at IS NULL"),
    )
