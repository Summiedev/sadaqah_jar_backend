"""initial mizan users foundation

Revision ID: 0001_initial_users
Revises:
Create Date: 2026-07-19

Baseline schema for the Mizan backend after the Authentication & User
Identity migration. Production and test environments apply this migration
chain with ``alembic upgrade head``.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_initial_users"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("mode", sa.String(length=20), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("avatar_data", sa.Text(), nullable=True),
        sa.Column("timezone", sa.String(length=64), nullable=True),
        sa.Column("locale", sa.String(length=16), nullable=True),
        sa.Column("last_active", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=False)
    op.create_index("ix_users_email_verified", "users", ["email_verified"], unique=False)
    op.create_index("ix_users_created_at", "users", ["created_at"], unique=False)
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"], unique=False)

    op.create_table(
        "user_preferences",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("theme", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("notification_preferences", sa.Text(), nullable=False),
        sa.Column("reminder_preferences", sa.Text(), nullable=False),
        sa.Column("accessibility_preferences", sa.Text(), nullable=False),
        sa.Column("privacy_preferences", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index("ix_user_sessions_token_hash", "user_sessions", ["token_hash"], unique=False)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_user_sessions_device_id", "user_sessions", ["device_id"], unique=False)
    op.create_index("ix_user_sessions_expires_at", "user_sessions", ["expires_at"], unique=False)
    op.create_index("ix_user_sessions_revoked_at", "user_sessions", ["revoked_at"], unique=False)
    op.create_index(
        "ix_user_sessions_user_active",
        "user_sessions",
        ["user_id", "revoked_at", "expires_at"],
        unique=False,
    )

    op.create_table(
        "user_devices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("platform", sa.String(length=16), nullable=False),
        sa.Column("device_name", sa.String(length=120), nullable=True),
        sa.Column("push_token", sa.String(length=512), nullable=True),
        sa.Column("last_active", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "device_id", name="uq_user_device"),
    )
    op.create_index("ix_user_devices_user_id", "user_devices", ["user_id"], unique=False)
    op.create_index("ix_user_devices_device_id", "user_devices", ["device_id"], unique=False)

    op.create_table(
        "email_verification_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        "ix_email_verification_tokens_token",
        "email_verification_tokens",
        ["token"],
        unique=False,
    )
    op.create_index(
        "ix_email_verification_tokens_user_id",
        "email_verification_tokens",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("used_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        "ix_password_reset_tokens_token", "password_reset_tokens", ["token"], unique=False
    )
    op.create_index(
        "ix_password_reset_tokens_user_id",
        "password_reset_tokens",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_password_reset_tokens_used_at", "password_reset_tokens", ["used_at"], unique=False
    )

    # ---- carried-forward tables (unchanged definitions) -----------------

    op.create_table(
        "jars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("current_stars", sa.Integer(), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_jars_id", "jars", ["id"], unique=False)
    op.create_index("ix_jars_user_id", "jars", ["user_id"], unique=False)

    op.create_table(
        "family_jars",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("invite_code", sa.String(length=20), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column("current_stars", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("last_activity_date", sa.Date(), nullable=True),
        sa.Column("streak_days", sa.Integer(), nullable=False),
        sa.Column("longest_streak", sa.Integer(), nullable=False),
        sa.Column("group_current_streak", sa.Integer(), nullable=True),
        sa.Column("group_longest_streak", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_index("ix_family_jars_id", "family_jars", ["id"], unique=False)
    op.create_index("ix_family_jars_invite_code", "family_jars", ["invite_code"], unique=False)
    op.create_index("ix_family_jars_created_by", "family_jars", ["created_by"], unique=False)
    op.create_index("ix_family_jars_is_active", "family_jars", ["is_active"], unique=False)

    op.create_table(
        "family_jar_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_jar_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_jar_id"], ["family_jars.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_family_jar_members_id", "family_jar_members", ["id"], unique=False
    )
    op.create_index(
        "ix_family_jar_members_family_jar_id",
        "family_jar_members",
        ["family_jar_id"],
        unique=False,
    )
    op.create_index(
        "ix_family_jar_members_user_id",
        "family_jar_members",
        ["user_id"],
        unique=False,
    )

    op.create_table(
        "family_jar_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_jar_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("act_id", sa.Integer(), nullable=False),
        sa.Column("stars_added", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("response_current_stars", sa.Integer(), nullable=True),
        sa.Column("response_capacity", sa.Integer(), nullable=True),
        sa.Column("response_completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_jar_id"], ["family_jars.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["act_id"], ["sadaqah_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "request_id", name="uq_family_jar_log_request"
        ),
    )
    op.create_index("ix_family_jar_logs_id", "family_jar_logs", ["id"], unique=False)
    op.create_index(
        "ix_family_jar_logs_user_id", "family_jar_logs", ["user_id"], unique=False
    )
    op.create_index(
        "ix_family_jar_logs_request_id", "family_jar_logs", ["request_id"], unique=False
    )
    op.create_index(
        "ix_family_jar_logs_user_date",
        "family_jar_logs",
        ["user_id", "date"],
        unique=False,
    )

    op.create_table(
        "sadaqah_acts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(length=20), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=True),
        sa.Column("is_ramadan_only", sa.Boolean(), nullable=True),
        sa.Column("ramadan_multiplier", sa.Integer(), nullable=True),
        sa.Column("difficulty", sa.Integer(), nullable=True),
        sa.Column("reward_weight", sa.Integer(), nullable=True),
        sa.Column("estimated_time_minutes", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sadaqah_acts_id", "sadaqah_acts", ["id"], unique=False)
    op.create_index(
        "ix_sadaqah_acts_verified_ramadan",
        "sadaqah_acts",
        ["verified", "is_ramadan_only"],
        unique=False,
    )

    op.create_table(
        "sadaqah_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("act_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.String(length=36), nullable=True),
        sa.Column("response_current_stars", sa.Integer(), nullable=True),
        sa.Column("response_capacity", sa.Integer(), nullable=True),
        sa.Column("response_completed_at", sa.DateTime(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("stars_earned", sa.Integer(), nullable=False),
        sa.Column("friday_boost", sa.Boolean(), nullable=True),
        sa.Column("ramadan_bonus", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["act_id"], ["sadaqah_acts.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "act_id", "date", name="unique_daily_log"
        ),
        sa.UniqueConstraint(
            "user_id", "request_id", name="unique_sadaqah_log_request"
        ),
    )
    op.create_index("ix_sadaqah_logs_id", "sadaqah_logs", ["id"], unique=False)
    op.create_index("ix_sadaqah_logs_user_id", "sadaqah_logs", ["user_id"], unique=False)
    op.create_index("ix_sadaqah_logs_act_id", "sadaqah_logs", ["act_id"], unique=False)
    op.create_index("ix_sadaqah_logs_request_id", "sadaqah_logs", ["request_id"], unique=False)
    op.create_index("ix_sadaqah_logs_user_date", "sadaqah_logs", ["user_id", "date"], unique=False)
    op.create_index("ix_sadaqah_logs_date", "sadaqah_logs", ["date"], unique=False)
    op.create_index("ix_sadaqah_logs_created_at", "sadaqah_logs", ["created_at"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notifications_id", "notifications", ["id"], unique=False)
    op.create_index(
        "ix_notifications_user_id", "notifications", ["user_id"], unique=False
    )

    op.create_table(
        "leaderboard_seasons",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("season_name", sa.String(length=100), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("season_name"),
    )
    op.create_index(
        "ix_leaderboard_seasons_id", "leaderboard_seasons", ["id"], unique=False
    )
    op.create_index(
        "ix_leaderboard_seasons_season_name",
        "leaderboard_seasons",
        ["season_name"],
        unique=False,
    )

    op.create_table(
        "badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_badges_id", "badges", ["id"], unique=False)

    op.create_table(
        "user_badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_badges_id", "user_badges", ["id"], unique=False)
    op.create_index("ix_user_badges_user_id", "user_badges", ["user_id"], unique=False)
    op.create_index("ix_user_badges_badge_id", "user_badges", ["badge_id"], unique=False)

    op.create_table(
        "family_badges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_id", sa.Integer(), nullable=False),
        sa.Column("badge_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["family_id"], ["family_jars.id"]),
        sa.ForeignKeyConstraint(["badge_id"], ["badges.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_family_badges_id", "family_badges", ["id"], unique=False)
    op.create_index("ix_family_badges_family_id", "family_badges", ["family_id"], unique=False)
    op.create_index("ix_family_badges_badge_id", "family_badges", ["badge_id"], unique=False)

    op.create_table(
        "evidences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("act_id", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("arabic_text", sa.Text(), nullable=True),
        sa.Column("english_text", sa.Text(), nullable=True),
        sa.Column("grade", sa.String(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["act_id"], ["sadaqah_acts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_evidences_id", "evidences", ["id"], unique=False)
    op.create_index("ix_evidences_act_id", "evidences", ["act_id"], unique=False)

    op.create_table(
        "charities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("website_url", sa.String(), nullable=False),
        sa.Column("category", sa.String(), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_featured", sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_charities_id", "charities", ["id"], unique=False)
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

    op.create_table(
        "donation_intents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("charity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["charity_id"], ["charities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_donation_intents_id", "donation_intents", ["id"], unique=False
    )
    op.create_index(
        "ix_donation_intents_user_id", "donation_intents", ["user_id"], unique=False
    )
    op.create_index(
        "ix_donation_intents_charity_id",
        "donation_intents",
        ["charity_id"],
        unique=False,
    )

    op.create_table(
        "user_streaks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("current_streak", sa.Integer(), nullable=True),
        sa.Column("longest_streak", sa.Integer(), nullable=True),
        sa.Column("last_completed_date", sa.Date(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_user_streaks_id", "user_streaks", ["id"], unique=False)
    op.create_index(
        "ix_user_streaks_user_id", "user_streaks", ["user_id"], unique=False
    )

    op.create_table(
        "adhkar",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("text_arabic", sa.Text(), nullable=False),
        sa.Column("text_translation", sa.Text(), nullable=False),
        sa.Column("time_of_day", sa.String(length=20), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("repeat_count", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_adhkar_id", "adhkar", ["id"], unique=False)
    op.create_index("ix_adhkar_time_of_day", "adhkar", ["time_of_day"], unique=False)


def downgrade() -> None:
    op.drop_table("adhkar")
    op.drop_table("user_streaks")
    op.drop_table("donation_intents")
    op.drop_table("charities")
    op.drop_table("evidences")
    op.drop_table("family_badges")
    op.drop_table("user_badges")
    op.drop_table("badges")
    op.drop_table("leaderboard_seasons")
    op.drop_table("notifications")
    op.drop_table("sadaqah_logs")
    op.drop_table("sadaqah_acts")
    op.drop_table("family_jar_logs")
    op.drop_table("family_jar_members")
    op.drop_table("family_jars")
    op.drop_table("jars")
    op.drop_table("password_reset_tokens")
    op.drop_table("email_verification_tokens")
    op.drop_table("user_devices")
    op.drop_table("user_sessions")
    op.drop_table("user_preferences")
    op.drop_table("users")
