"""Add user coordinates and durable prayer-relative reminder schedules."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "20260726_prayer_reminder_scheduling"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("latitude", sa.Float(), nullable=True))
    op.add_column("users", sa.Column("longitude", sa.Float(), nullable=True))
    op.create_table(
        "scheduled_notifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("local_date", sa.String(length=10), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="scheduled"),
        sa.Column("celery_task_id", sa.String(length=64), nullable=True),
        sa.Column("delivered_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["notification_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "template_id", "local_date", name="uq_scheduled_notification_daily"),
    )
    op.create_index("ix_scheduled_notifications_due", "scheduled_notifications", ["status", "scheduled_for"])
    op.create_index("ix_scheduled_notifications_user_id", "scheduled_notifications", ["user_id"])
    op.create_index("ix_scheduled_notifications_scheduled_for", "scheduled_notifications", ["scheduled_for"])


def downgrade() -> None:
    op.drop_table("scheduled_notifications")
    op.drop_column("users", "longitude")
    op.drop_column("users", "latitude")
