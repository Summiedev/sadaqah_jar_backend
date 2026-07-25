"""create books domain

Revision ID: 0006_create_books
Revises: 0005_add_note_to_sadaqah_logs
Create Date: 2026-07-25 08:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0006_create_books"
down_revision: Union[str, Sequence[str], None] = "0005_add_note_to_sadaqah_logs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "books",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("author", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover_url", sa.String(512), nullable=True),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("language", sa.String(8), nullable=False, server_default="en"),
        sa.Column("published", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("deleted_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_books_category", "books", ["category"])
    op.create_index("ix_books_published", "books", ["published"])
    op.create_index("ix_books_deleted_at", "books", ["deleted_at"])

    op.create_table(
        "book_chapters",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("book_id", sa.Integer(), sa.ForeignKey("books.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chapter_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("reading_time_minutes", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_book_chapters_book_id", "book_chapters", ["book_id"])
    op.create_index("ix_book_chapter_number", "book_chapters", ["book_id", "chapter_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_book_chapter_number", table_name="book_chapters")
    op.drop_index("ix_book_chapters_book_id", table_name="book_chapters")
    op.drop_table("book_chapters")
    op.drop_index("ix_books_deleted_at", table_name="books")
    op.drop_index("ix_books_published", table_name="books")
    op.drop_index("ix_books_category", table_name="books")
    op.drop_table("books")
