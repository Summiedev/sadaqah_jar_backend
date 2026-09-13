"""add one weekly shared family intention and private contributions."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f6a7b8c9d0e1"
# The repository historically has two migration branches (the personal-goal
# constraint and the family/reflection branch). Joining both here keeps a
# fresh production database on one unambiguous head.
down_revision: Union[str, Sequence[str], None] = (
    "e1f4c9d2a7b1",
    "f1a2b3c4d5e6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_intentions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "family_id",
            sa.Integer(),
            sa.ForeignKey("families.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("week_start", sa.Date(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("family_id", "week_start", name="uq_family_intention_week"),
    )
    op.create_index("ix_family_intentions_id", "family_intentions", ["id"])
    op.create_index("ix_family_intentions_family_id", "family_intentions", ["family_id"])
    op.create_index(
        "ix_family_intentions_current",
        "family_intentions",
        ["family_id", "week_start", "deleted_at"],
    )
    op.create_table(
        "family_intention_contributions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "intention_id",
            sa.Integer(),
            sa.ForeignKey("family_intentions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("private_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "intention_id", "user_id", name="uq_family_intention_contributor"
        ),
    )
    op.create_index(
        "ix_family_intention_contributions_id",
        "family_intention_contributions",
        ["id"],
    )
    op.create_index(
        "ix_family_intention_contributions_intention_id",
        "family_intention_contributions",
        ["intention_id"],
    )
    op.create_index(
        "ix_family_intention_contributions_user",
        "family_intention_contributions",
        ["user_id", "intention_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_family_intention_contributions_user",
        table_name="family_intention_contributions",
    )
    op.drop_index(
        "ix_family_intention_contributions_intention_id",
        table_name="family_intention_contributions",
    )
    op.drop_index(
        "ix_family_intention_contributions_id",
        table_name="family_intention_contributions",
    )
    op.drop_table("family_intention_contributions")
    op.drop_index("ix_family_intentions_current", table_name="family_intentions")
    op.drop_index("ix_family_intentions_family_id", table_name="family_intentions")
    op.drop_index("ix_family_intentions_id", table_name="family_intentions")
    op.drop_table("family_intentions")
