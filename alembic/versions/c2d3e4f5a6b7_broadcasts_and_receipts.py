"""add in-app broadcasts and per-user receipts"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "broadcasts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("image_url", sa.String(length=1024), nullable=True),
        sa.Column("cta_label", sa.String(length=80), nullable=True),
        sa.Column("cta_link", sa.String(length=1024), nullable=True),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=True),
        sa.Column("audience", sa.String(length=32), nullable=False),
        sa.Column("display_mode", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_broadcasts_id", "broadcasts", ["id"], unique=False)
    op.create_index(
        "ix_broadcasts_active_window", "broadcasts", ["is_active", "starts_at", "ends_at"], unique=False
    )
    op.create_table(
        "broadcast_receipts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("broadcast_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(), nullable=True),
        sa.Column("clicked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["broadcast_id"], ["broadcasts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "broadcast_id", name="uq_broadcast_receipt_user_broadcast"),
    )
    op.create_index("ix_broadcast_receipts_id", "broadcast_receipts", ["id"], unique=False)
    op.create_index(
        "ix_broadcast_receipts_user_broadcast", "broadcast_receipts", ["user_id", "broadcast_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_broadcast_receipts_user_broadcast", table_name="broadcast_receipts")
    op.drop_index("ix_broadcast_receipts_id", table_name="broadcast_receipts")
    op.drop_table("broadcast_receipts")
    op.drop_index("ix_broadcasts_active_window", table_name="broadcasts")
    op.drop_index("ix_broadcasts_id", table_name="broadcasts")
    op.drop_table("broadcasts")
