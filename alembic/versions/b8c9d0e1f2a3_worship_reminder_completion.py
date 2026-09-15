"""persist Salah check-offs and normalize worship reminders"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "journey_prayer_completions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("local_date", sa.Date(), nullable=False),
        sa.Column("prayer_name", sa.String(length=12), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint(
            "user_id", "local_date", "prayer_name", name="uq_journey_prayer_day"
        ),
    )
    op.create_index(
        "ix_journey_prayer_completions_user_id",
        "journey_prayer_completions",
        ["user_id"],
    )
    op.create_index(
        "ix_journey_prayer_completions_id",
        "journey_prayer_completions",
        ["id"],
    )
    op.create_index(
        "ix_journey_prayer_completions_created_at",
        "journey_prayer_completions",
        ["created_at"],
    )
    op.create_index(
        "ix_journey_prayer_user_date",
        "journey_prayer_completions",
        ["user_id", "local_date"],
    )

    templates = sa.table(
        "notification_templates",
        sa.column("key", sa.String(64)),
        sa.column("title_template", sa.String(255)),
        sa.column("message_template", sa.Text()),
        sa.column("category", sa.String(32)),
        sa.column("strategy", sa.String(32)),
        sa.column("strategy_config", sa.Text()),
        sa.column("enabled", sa.Boolean()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    bind = op.get_bind()
    normalized_categories = {
        "morning_adhkar": "adhkar_morning",
        "morning_adhkar_expanded": "adhkar_morning",
        "evening_adhkar": "adhkar_evening",
        "evening_adhkar_expanded": "adhkar_evening",
        "quran_reminder": "quran",
        "salatul_duha": "prayer_nafl",
        "duha_reminder": "prayer_nafl",
        "witr_reminder": "prayer_nafl",
        "witr_reminder_expanded": "prayer_nafl",
        "tahajjud_reminder": "prayer_nafl",
        "pre_fajr": "prayer_fardh",
        "pre_dhuhr": "prayer_fardh",
        "pre_maghrib": "prayer_fardh",
        "pre_isha": "prayer_fardh",
    }
    for key, category in normalized_categories.items():
        bind.execute(
            templates.update()
            .where(templates.c.key == key)
            .values(category=category)
        )

    salah = (
        ("fajr_reminder", "fajr", "Fajr"),
        ("dhuhr_reminder", "zuhr", "Dhuhr"),
        ("asr_reminder", "asr", "Asr"),
        ("maghrib_reminder", "maghrib", "Maghrib"),
        ("isha_reminder", "isha", "Isha"),
    )
    for key, anchor, name in salah:
        existing = bind.execute(
            sa.select(templates.c.key).where(templates.c.key == key)
        ).first()
        if existing is not None:
            bind.execute(
                templates.update()
                .where(templates.c.key == key)
                .values(
                    category="prayer_fardh",
                    title_template="{title}",
                    message_template="{message}",
                )
            )
            continue
        bind.execute(
            templates.insert().values(
                key=key,
                title_template="{title}",
                message_template="{message}",
                category="prayer_fardh",
                strategy="prayer_relative",
                strategy_config=(
                    '{"anchor": "' + anchor
                    + '", "offset_minutes": 0, "content_source": "prayer_fardh", "prayer_name": "'
                    + name.lower()
                    + '"}'
                ),
                enabled=True,
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    op.drop_index("ix_journey_prayer_user_date", table_name="journey_prayer_completions")
    op.drop_index("ix_journey_prayer_completions_created_at", table_name="journey_prayer_completions")
    op.drop_index("ix_journey_prayer_completions_id", table_name="journey_prayer_completions")
    op.drop_index("ix_journey_prayer_completions_user_id", table_name="journey_prayer_completions")
    op.drop_table("journey_prayer_completions")
