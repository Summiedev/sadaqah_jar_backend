"""add indexes for database-paginated journey history.

Revision ID: d6e7f8a9b0c1
Revises: c3d4e5f6a7b8
"""

from typing import Sequence, Union

from alembic import op


revision: str = "d6e7f8a9b0c1"
down_revision: Union[str, Sequence[str], None] = "c3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_family_activities_actor_created",
        "family_activities",
        ["actor_id", "created_at", "id"],
    )
    op.create_index(
        "ix_journey_prayer_user_completed",
        "journey_prayer_completions",
        ["user_id", "completed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_journey_prayer_user_completed",
        table_name="journey_prayer_completions",
    )
    op.drop_index(
        "ix_family_activities_actor_created",
        table_name="family_activities",
    )
