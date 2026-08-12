"""add quran mushaf tables

Revision ID: 7c3b2a1f9e4d
Revises: e1f4c9d2a7b1
Create Date: 2026-08-11 00:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "7c3b2a1f9e4d"
down_revision: str | Sequence[str] | None = "e1f4c9d2a7b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "quran_surahs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name_ar", sa.String(length=120), nullable=False),
        sa.Column("name_en", sa.String(length=120), nullable=False),
        sa.Column("name_transliteration", sa.String(length=120), nullable=False),
        sa.Column("revelation_type", sa.String(length=30), nullable=False),
        sa.Column("ayah_count", sa.Integer(), nullable=False),
        sa.Column("bismillah_pre", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "quran_page_assets",
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("local_storage_key", sa.Text(), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.PrimaryKeyConstraint("page_number"),
    )
    op.create_table(
        "quran_ayahs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("verse_key", sa.String(length=12), nullable=False),
        sa.Column("surah_id", sa.Integer(), nullable=False),
        sa.Column("ayah_number", sa.Integer(), nullable=False),
        sa.Column("text_uthmani", sa.Text(), nullable=False),
        sa.Column("text_uthmani_tajweed", sa.Text(), nullable=True),
        sa.Column("text_simple", sa.Text(), nullable=True),
        sa.Column("juz_number", sa.Integer(), nullable=False),
        sa.Column("hizb_number", sa.Integer(), nullable=False),
        sa.Column("hizb_quarter", sa.Integer(), nullable=True),
        sa.Column("manzil_number", sa.Integer(), nullable=True),
        sa.Column("ruku_number", sa.Integer(), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("sajda", sa.Boolean(), nullable=False),
        sa.Column("sajda_type", sa.String(length=30), nullable=True),
        sa.ForeignKeyConstraint(["surah_id"], ["quran_surahs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("verse_key", name="uq_quran_ayahs_verse_key"),
    )
    op.create_index(
        "ix_quran_ayahs_surah_ayah", "quran_ayahs", ["surah_id", "ayah_number"]
    )
    op.create_index("ix_quran_ayahs_juz", "quran_ayahs", ["juz_number"])
    op.create_index("ix_quran_ayahs_hizb", "quran_ayahs", ["hizb_number"])
    op.create_index("ix_quran_ayahs_page", "quran_ayahs", ["page_number"])
    op.create_index("ix_quran_ayahs_verse_key", "quran_ayahs", ["verse_key"])
    op.create_table(
        "quran_translations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ayah_id", sa.Integer(), nullable=False),
        sa.Column("edition_code", sa.String(length=80), nullable=False),
        sa.Column("language", sa.String(length=12), nullable=False),
        sa.Column("translator_name", sa.String(length=160), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["ayah_id"], ["quran_ayahs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ayah_id", "edition_code", name="uq_quran_translation_ayah_edition"
        ),
    )
    op.create_index(
        "ix_quran_translations_edition", "quran_translations", ["edition_code"]
    )
    op.create_table(
        "quran_transliterations",
        sa.Column("ayah_id", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["ayah_id"], ["quran_ayahs.id"]),
        sa.PrimaryKeyConstraint("ayah_id"),
    )
    op.create_table(
        "quran_audio_segments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("ayah_id", sa.Integer(), nullable=False),
        sa.Column("reciter_id", sa.String(length=80), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["ayah_id"], ["quran_ayahs.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "ayah_id", "reciter_id", name="uq_quran_audio_ayah_reciter"
        ),
    )
    op.create_index("ix_quran_audio_reciter", "quran_audio_segments", ["reciter_id"])
    op.create_table(
        "quran_bookmarks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("verse_key", sa.String(length=12), nullable=True),
        sa.Column("page_number", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "verse_key", "page_number", name="uq_quran_bookmark"
        ),
    )
    op.create_index(
        "ix_quran_bookmarks_user", "quran_bookmarks", ["user_id", "created_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_quran_bookmarks_user", table_name="quran_bookmarks")
    op.drop_table("quran_bookmarks")
    op.drop_index("ix_quran_audio_reciter", table_name="quran_audio_segments")
    op.drop_table("quran_audio_segments")
    op.drop_table("quran_transliterations")
    op.drop_index("ix_quran_translations_edition", table_name="quran_translations")
    op.drop_table("quran_translations")
    op.drop_index("ix_quran_ayahs_verse_key", table_name="quran_ayahs")
    op.drop_index("ix_quran_ayahs_page", table_name="quran_ayahs")
    op.drop_index("ix_quran_ayahs_hizb", table_name="quran_ayahs")
    op.drop_index("ix_quran_ayahs_juz", table_name="quran_ayahs")
    op.drop_index("ix_quran_ayahs_surah_ayah", table_name="quran_ayahs")
    op.drop_table("quran_ayahs")
    op.drop_table("quran_page_assets")
    op.drop_table("quran_surahs")
