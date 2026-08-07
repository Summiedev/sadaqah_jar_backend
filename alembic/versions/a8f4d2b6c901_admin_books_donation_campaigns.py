"""admin books and donation campaigns

Revision ID: a8f4d2b6c901
Revises: 29cec215c274
Create Date: 2026-08-07 16:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a8f4d2b6c901"
down_revision: Union[str, Sequence[str], None] = "29cec215c274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "books", sa.Column("file_format", sa.String(length=16), nullable=True)
    )
    op.create_index(
        op.f("ix_books_file_format"), "books", ["file_format"], unique=False
    )
    op.create_table(
        "book_pages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("book_id", sa.Integer(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=512), nullable=False),
        sa.Column("image_type", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["book_id"], ["books.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("book_id", "page_number", name="uq_book_page_number"),
    )
    op.create_index(op.f("ix_book_pages_id"), "book_pages", ["id"], unique=False)
    op.create_index(
        "ix_book_pages_book_order",
        "book_pages",
        ["book_id", "page_number"],
        unique=False,
    )
    op.create_index(
        op.f("ix_book_pages_book_id"), "book_pages", ["book_id"], unique=False
    )

    op.add_column("charities", sa.Column("title", sa.String(length=255), nullable=True))
    op.add_column(
        "charities",
        sa.Column(
            "donation_type",
            sa.String(length=24),
            nullable=False,
            server_default="external",
        ),
    )
    op.add_column(
        "charities", sa.Column("case_name", sa.String(length=255), nullable=True)
    )
    op.add_column("charities", sa.Column("external_url", sa.String(), nullable=True))
    op.add_column(
        "charities", sa.Column("target_amount", sa.Numeric(12, 2), nullable=True)
    )
    op.add_column(
        "charities", sa.Column("amount_raised", sa.Numeric(12, 2), nullable=True)
    )
    op.add_column(
        "charities",
        sa.Column(
            "currency", sa.String(length=8), nullable=False, server_default="NGN"
        ),
    )
    op.add_column("charities", sa.Column("image_urls", sa.JSON(), nullable=True))
    op.add_column("charities", sa.Column("evidence", sa.Text(), nullable=True))
    op.add_column("charities", sa.Column("evidence_urls", sa.JSON(), nullable=True))
    op.add_column("charities", sa.Column("contact_info", sa.Text(), nullable=True))
    op.add_column(
        "charities",
        sa.Column(
            "status", sa.String(length=24), nullable=False, server_default="active"
        ),
    )
    op.add_column("charities", sa.Column("deadline", sa.Date(), nullable=True))
    op.add_column(
        "charities",
        sa.Column(
            "is_published", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    op.execute(
        "UPDATE charities SET external_url = website_url WHERE external_url IS NULL"
    )
    op.create_index(
        op.f("ix_charities_donation_type"), "charities", ["donation_type"], unique=False
    )
    op.create_index(op.f("ix_charities_status"), "charities", ["status"], unique=False)
    op.create_index(
        op.f("ix_charities_is_published"), "charities", ["is_published"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_charities_is_published"), table_name="charities")
    op.drop_index(op.f("ix_charities_status"), table_name="charities")
    op.drop_index(op.f("ix_charities_donation_type"), table_name="charities")
    op.drop_column("charities", "is_published")
    op.drop_column("charities", "deadline")
    op.drop_column("charities", "status")
    op.drop_column("charities", "contact_info")
    op.drop_column("charities", "evidence_urls")
    op.drop_column("charities", "evidence")
    op.drop_column("charities", "image_urls")
    op.drop_column("charities", "currency")
    op.drop_column("charities", "amount_raised")
    op.drop_column("charities", "target_amount")
    op.drop_column("charities", "external_url")
    op.drop_column("charities", "case_name")
    op.drop_column("charities", "donation_type")
    op.drop_column("charities", "title")

    op.drop_index(op.f("ix_book_pages_book_id"), table_name="book_pages")
    op.drop_index("ix_book_pages_book_order", table_name="book_pages")
    op.drop_index(op.f("ix_book_pages_id"), table_name="book_pages")
    op.drop_table("book_pages")
    op.drop_index(op.f("ix_books_file_format"), table_name="books")
    op.drop_column("books", "file_format")
