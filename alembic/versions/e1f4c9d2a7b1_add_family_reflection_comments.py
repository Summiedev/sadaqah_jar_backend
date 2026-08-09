"""add family reflection comments

Revision ID: e1f4c9d2a7b1
Revises: b40d9d5fddae
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e1f4c9d2a7b1"
down_revision: Union[str, Sequence[str], None] = "b40d9d5fddae"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "family_reflection_comments",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("reflection_id", sa.Integer(), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["reflection_id"], ["family_reflections.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_family_reflection_comments_id", "family_reflection_comments", ["id"])
    op.create_index("ix_family_reflection_comments_reflection_id", "family_reflection_comments", ["reflection_id"])
    op.create_index("ix_family_reflection_comments_author_id", "family_reflection_comments", ["author_id"])
    op.create_index("ix_family_reflection_comments_deleted_at", "family_reflection_comments", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_family_reflection_comments_deleted_at", table_name="family_reflection_comments")
    op.drop_index("ix_family_reflection_comments_author_id", table_name="family_reflection_comments")
    op.drop_index("ix_family_reflection_comments_reflection_id", table_name="family_reflection_comments")
    op.drop_index("ix_family_reflection_comments_id", table_name="family_reflection_comments")
    op.drop_table("family_reflection_comments")
