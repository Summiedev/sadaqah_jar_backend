"""Drop unique_daily_log constraint to allow duplicate sadaqah acts per day.

The application code comment states that duplicate acts are allowed — every
sincere act counts, even if repeated.  The unique constraint on
(user_id, act_id, date) prevented this, causing IntegrityError on second
submission of the same act in a single day.

Revision ID: 20260731_101300
Revises:
Create Date: 2026-07-31 10:13:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "20260731_101300"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("unique_daily_log", "sadaqah_logs", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "unique_daily_log",
        "sadaqah_logs",
        ["user_id", "act_id", "date"],
    )