"""add opt-in nawafil reminders after selected salah"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, Sequence[str], None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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
    reminders = (
        ("nawafil_after_dhuhr", "zuhr", "dhuhr"),
        ("nawafil_after_maghrib", "maghrib", "maghrib"),
        ("nawafil_after_isha", "isha", "isha"),
    )
    for key, anchor, prayer in reminders:
        exists = bind.execute(
            sa.select(templates.c.key).where(templates.c.key == key)
        ).first()
        if exists is not None:
            continue
        bind.execute(
            templates.insert().values(
                key=key,
                title_template="{title}",
                message_template="{message}",
                category="prayer_nafl",
                strategy="prayer_relative",
                strategy_config=(
                    '{"anchor": "'
                    + anchor
                    + '", "offset_minutes": 15, "prayer_name": "'
                    + prayer
                    + '", "content_source": "prayer_nafl", "deep_link": "/home"}'
                ),
                enabled=True,
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    # Keep templates intact so existing scheduled rows and notification audit
    # history remain valid if the application revision is rolled back.
    pass
