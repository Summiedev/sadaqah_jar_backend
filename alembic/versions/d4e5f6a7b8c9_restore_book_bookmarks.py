"""restore book bookmarks removed by an earlier migration."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "book_bookmarks",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "book_id",
            sa.Integer(),
            sa.ForeignKey("books.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chapter_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "book_id", name="uq_book_bookmark_user_book"),
    )
    op.create_index("ix_book_bookmarks_id", "book_bookmarks", ["id"])
    op.create_index("ix_book_bookmarks_user_id", "book_bookmarks", ["user_id"])
    op.create_index("ix_book_bookmarks_book_id", "book_bookmarks", ["book_id"])
    op.create_index("ix_book_bookmarks_created_at", "book_bookmarks", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_book_bookmarks_created_at", table_name="book_bookmarks")
    op.drop_index("ix_book_bookmarks_book_id", table_name="book_bookmarks")
    op.drop_index("ix_book_bookmarks_user_id", table_name="book_bookmarks")
    op.drop_index("ix_book_bookmarks_id", table_name="book_bookmarks")
    op.drop_table("book_bookmarks")
