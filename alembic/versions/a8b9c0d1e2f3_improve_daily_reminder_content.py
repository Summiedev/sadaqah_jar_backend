"""improve daily reminder content and add a durable reflection prompt."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, Sequence[str], None] = "f7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _template_table() -> sa.sql.expression.TableClause:
    return sa.table(
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


def upgrade() -> None:
    templates = _template_table()
    bind = op.get_bind()

    updates = {
        "morning_adhkar": (
            "Morning adhkar",
            "{arabic}\n{translation}\n{source} · Repeat {repeat_count}×\nA gentle start: recite with presence and carry this remembrance into your morning.",
        ),
        "quran_reminder": (
            "A page with the Quran",
            "Take a few quiet minutes with the Quran today. Even one page is a meaningful step.",
        ),
        "random_sadaqah_prompt": (
            "A small sadaqah",
            "{title}. {message} A small act, offered sincerely, is never small with Allah.",
        ),
        "reflection_prompt": (
            "{title}",
            "{message}\nWrite one honest line in Mizan, then choose one small action to carry forward.",
        ),
    }
    for key, (title, message) in updates.items():
        bind.execute(
            templates.update()
            .where(templates.c.key == key)
            .values(title_template=title, message_template=message)
        )

    reflection = bind.execute(
        sa.select(templates.c.key).where(templates.c.key == "reflection_prompt")
    ).first()
    if reflection is None:
        bind.execute(
            templates.insert().values(
                key="reflection_prompt",
                title_template="{title}",
                message_template=(
                    "{message}\nWrite one honest line in Mizan, then choose one small action to carry forward."
                ),
                category="reflection",
                strategy="prayer_relative",
                strategy_config='{"anchor": "isha", "offset_minutes": 15, "content_source": "reflection"}',
                enabled=True,
                created_at=sa.func.now(),
                updated_at=sa.func.now(),
            )
        )


def downgrade() -> None:
    # Content migrations are intentionally not destructive. Existing users may
    # have received or edited these template definitions in the admin UI.
    pass
