from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuranSurah(Base):
    __tablename__ = "quran_surahs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name_ar: Mapped[str] = mapped_column(String(120), nullable=False)
    name_en: Mapped[str] = mapped_column(String(120), nullable=False)
    name_transliteration: Mapped[str] = mapped_column(String(120), nullable=False)
    revelation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ayah_count: Mapped[int] = mapped_column(Integer, nullable=False)
    bismillah_pre: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    ayahs: Mapped[list["QuranAyah"]] = relationship(back_populates="surah")


class QuranAyah(Base):
    __tablename__ = "quran_ayahs"
    __table_args__ = (
        UniqueConstraint("verse_key", name="uq_quran_ayahs_verse_key"),
        Index("ix_quran_ayahs_surah_ayah", "surah_id", "ayah_number"),
        Index("ix_quran_ayahs_juz", "juz_number"),
        Index("ix_quran_ayahs_hizb", "hizb_number"),
        Index("ix_quran_ayahs_page", "page_number"),
        Index("ix_quran_ayahs_verse_key", "verse_key"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    verse_key: Mapped[str] = mapped_column(String(12), nullable=False)
    surah_id: Mapped[int] = mapped_column(ForeignKey("quran_surahs.id"), nullable=False)
    ayah_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text_uthmani: Mapped[str] = mapped_column(Text, nullable=False)
    text_uthmani_tajweed: Mapped[str | None] = mapped_column(Text)
    text_simple: Mapped[str | None] = mapped_column(Text)
    juz_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hizb_number: Mapped[int] = mapped_column(Integer, nullable=False)
    hizb_quarter: Mapped[int | None] = mapped_column(Integer)
    manzil_number: Mapped[int | None] = mapped_column(Integer)
    ruku_number: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sajda: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sajda_type: Mapped[str | None] = mapped_column(String(30))

    surah: Mapped[QuranSurah] = relationship(back_populates="ayahs")
    translations: Mapped[list["QuranTranslation"]] = relationship(
        back_populates="ayah", cascade="all, delete-orphan"
    )
    transliteration: Mapped["QuranTransliteration | None"] = relationship(
        back_populates="ayah", cascade="all, delete-orphan"
    )
    audio_segments: Mapped[list["QuranAudioSegment"]] = relationship(
        back_populates="ayah", cascade="all, delete-orphan"
    )


class QuranTranslation(Base):
    __tablename__ = "quran_translations"
    __table_args__ = (
        UniqueConstraint(
            "ayah_id", "edition_code", name="uq_quran_translation_ayah_edition"
        ),
        Index("ix_quran_translations_edition", "edition_code"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ayah_id: Mapped[int] = mapped_column(ForeignKey("quran_ayahs.id"), nullable=False)
    edition_code: Mapped[str] = mapped_column(String(80), nullable=False)
    language: Mapped[str] = mapped_column(String(12), nullable=False)
    translator_name: Mapped[str] = mapped_column(String(160), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    ayah: Mapped[QuranAyah] = relationship(back_populates="translations")


class QuranTransliteration(Base):
    __tablename__ = "quran_transliterations"

    ayah_id: Mapped[int] = mapped_column(ForeignKey("quran_ayahs.id"), primary_key=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)

    ayah: Mapped[QuranAyah] = relationship(back_populates="transliteration")


class QuranAudioSegment(Base):
    __tablename__ = "quran_audio_segments"
    __table_args__ = (
        UniqueConstraint("ayah_id", "reciter_id", name="uq_quran_audio_ayah_reciter"),
        Index("ix_quran_audio_reciter", "reciter_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ayah_id: Mapped[int] = mapped_column(ForeignKey("quran_ayahs.id"), nullable=False)
    reciter_id: Mapped[str] = mapped_column(String(80), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int | None] = mapped_column(Integer)
    end_ms: Mapped[int | None] = mapped_column(Integer)

    ayah: Mapped[QuranAyah] = relationship(back_populates="audio_segments")


class QuranPageAsset(Base):
    __tablename__ = "quran_page_assets"

    page_number: Mapped[int] = mapped_column(Integer, primary_key=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    local_storage_key: Mapped[str | None] = mapped_column(Text)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(120), nullable=False)


class QuranBookmark(Base):
    __tablename__ = "quran_bookmarks"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "verse_key", "page_number", name="uq_quran_bookmark"
        ),
        Index("ix_quran_bookmarks_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    verse_key: Mapped[str | None] = mapped_column(String(12))
    page_number: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
