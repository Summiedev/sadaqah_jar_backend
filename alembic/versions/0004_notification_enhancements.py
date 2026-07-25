"""add notification enhancements

Revision ID: 0004_notification_enhancements
Revises: 0003_move_user_configuration_to_preferences
Create Date: 2026-07-20 12:21:05.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0004_notification_enhancements"
down_revision: Union[str, None] = "0003_move_user_configuration_to_preferences"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("notifications", sa.Column("category", sa.String(length=32), nullable=True))
    op.add_column("notifications", sa.Column("action", sa.Text(), nullable=True))
    op.create_index("ix_notifications_user_created", "notifications", ["user_id", "created_at"])
    op.create_index("ix_notifications_user_unread", "notifications", ["user_id", "is_read"])

    op.create_table(
        "notification_templates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=64), nullable=False),
        sa.Column("title_template", sa.String(length=255), nullable=False),
        sa.Column("message_template", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=32), nullable=False),
        sa.Column("strategy", sa.String(length=32), nullable=False),
        sa.Column("strategy_config", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key", name="uq_notification_templates_key"),
    )
    op.create_index("ix_notification_templates_key", "notification_templates", ["key"], unique=False)
    op.create_index("ix_notification_templates_category", "notification_templates", ["category"], unique=False)
    op.create_index("ix_notification_templates_strategy", "notification_templates", ["strategy"], unique=False)
    op.create_index("ix_notification_templates_enabled", "notification_templates", ["enabled"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_notification_templates_enabled", table_name="notification_templates")
    op.drop_index("ix_notification_templates_strategy", table_name="notification_templates")
    op.drop_index("ix_notification_templates_category", table_name="notification_templates")
    op.drop_index("ix_notification_templates_key", table_name="notification_templates")
    op.drop_table("notification_templates")

    op.drop_index("ix_notifications_user_unread", table_name="notifications")
    op.drop_index("ix_notifications_user_created", table_name="notifications")
    op.drop_column("notifications", "action")
    op.drop_column("notifications", "category")
