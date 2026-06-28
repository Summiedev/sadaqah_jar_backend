"""add performance indexes

Revision ID: 8a4d7e1b9c2f
Revises: 91740e749e36
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8a4d7e1b9c2f"
down_revision: Union[str, Sequence[str], None] = "91740e749e36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_charities_verified_active_category",
        "charities",
        ["is_verified", "is_active", "category"],
        unique=False,
    )
    op.create_index(
        "ix_charities_verified_active_featured",
        "charities",
        ["is_verified", "is_active", "is_featured"],
        unique=False,
    )
    op.create_index("ix_donation_intents_user_id", "donation_intents", ["user_id"], unique=False)
    op.create_index("ix_donation_intents_charity_id", "donation_intents", ["charity_id"], unique=False)
    op.create_index("ix_family_jars_created_by", "family_jars", ["created_by"], unique=False)
    op.create_index("ix_family_jars_is_active", "family_jars", ["is_active"], unique=False)
    op.create_index("ix_family_jar_members_family_jar_id", "family_jar_members", ["family_jar_id"], unique=False)
    op.create_index("ix_family_jar_members_user_id", "family_jar_members", ["user_id"], unique=False)
    op.create_index("ix_sadaqah_acts_verified_ramadan", "sadaqah_acts", ["verified", "is_ramadan_only"], unique=False)
    op.create_index("ix_sadaqah_logs_created_at", "sadaqah_logs", ["created_at"], unique=False)
    op.create_index("ix_users_is_active", "users", ["is_active"], unique=False)
    op.create_index("ix_users_friday_reminder", "users", ["friday_reminder"], unique=False)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_created_at", table_name="users")
    op.drop_index("ix_users_friday_reminder", table_name="users")
    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_sadaqah_logs_created_at", table_name="sadaqah_logs")
    op.drop_index("ix_sadaqah_acts_verified_ramadan", table_name="sadaqah_acts")
    op.drop_index("ix_family_jar_members_user_id", table_name="family_jar_members")
    op.drop_index("ix_family_jar_members_family_jar_id", table_name="family_jar_members")
    op.drop_index("ix_family_jars_is_active", table_name="family_jars")
    op.drop_index("ix_family_jars_created_by", table_name="family_jars")
    op.drop_index("ix_donation_intents_charity_id", table_name="donation_intents")
    op.drop_index("ix_donation_intents_user_id", table_name="donation_intents")
    op.drop_index("ix_charities_verified_active_featured", table_name="charities")
    op.drop_index("ix_charities_verified_active_category", table_name="charities")
