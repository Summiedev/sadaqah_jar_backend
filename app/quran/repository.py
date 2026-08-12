from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, selectinload

from app.quran.models import (
    QuranAyah,
    QuranBookmark,
    QuranPageAsset,
    QuranSurah,
    QuranTranslation,
)


_AYAH_LOAD = (
    selectinload(QuranAyah.translations),
    selectinload(QuranAyah.transliteration),
    selectinload(QuranAyah.audio_segments),
)


def list_surahs(db: Session) -> list[QuranSurah]:
    return list(db.scalars(select(QuranSurah).order_by(QuranSurah.id.asc())).all())


def get_surah(db: Session, surah_id: int) -> QuranSurah | None:
    return db.get(QuranSurah, surah_id)


def ayahs_for_surah(db: Session, surah_id: int) -> list[QuranAyah]:
    return list(
        db.scalars(
            select(QuranAyah)
            .options(*_AYAH_LOAD)
            .where(QuranAyah.surah_id == surah_id)
            .order_by(QuranAyah.ayah_number.asc())
        ).all()
    )


def ayahs_for_page(db: Session, page_number: int) -> list[QuranAyah]:
    return list(
        db.scalars(
            select(QuranAyah)
            .options(*_AYAH_LOAD)
            .where(QuranAyah.page_number == page_number)
            .order_by(QuranAyah.surah_id.asc(), QuranAyah.ayah_number.asc())
        ).all()
    )


def ayahs_for_juz(db: Session, juz_number: int) -> list[QuranAyah]:
    return list(
        db.scalars(
            select(QuranAyah)
            .options(*_AYAH_LOAD)
            .where(QuranAyah.juz_number == juz_number)
            .order_by(QuranAyah.surah_id.asc(), QuranAyah.ayah_number.asc())
        ).all()
    )


def ayahs_for_hizb(db: Session, hizb_number: int) -> list[QuranAyah]:
    return list(
        db.scalars(
            select(QuranAyah)
            .options(*_AYAH_LOAD)
            .where(QuranAyah.hizb_number == hizb_number)
            .order_by(QuranAyah.surah_id.asc(), QuranAyah.ayah_number.asc())
        ).all()
    )


def get_page_asset(db: Session, page_number: int) -> QuranPageAsset | None:
    return db.get(QuranPageAsset, page_number)


def search(db: Session, query: str, limit: int) -> list[QuranAyah]:
    pattern = f"%{query}%"
    return list(
        db.scalars(
            select(QuranAyah)
            .join(QuranSurah)
            .outerjoin(QuranTranslation)
            .options(*_AYAH_LOAD, selectinload(QuranAyah.surah))
            .where(
                or_(
                    QuranAyah.verse_key == query,
                    QuranAyah.text_uthmani.ilike(pattern),
                    QuranAyah.text_simple.ilike(pattern),
                    QuranSurah.name_en.ilike(pattern),
                    QuranSurah.name_transliteration.ilike(pattern),
                    QuranTranslation.text.ilike(pattern),
                )
            )
            .distinct()
            .order_by(QuranAyah.surah_id.asc(), QuranAyah.ayah_number.asc())
            .limit(limit)
        ).all()
    )


def list_bookmarks(db: Session, user_id: int) -> list[QuranBookmark]:
    return list(
        db.scalars(
            select(QuranBookmark)
            .where(QuranBookmark.user_id == user_id)
            .order_by(QuranBookmark.created_at.desc())
        ).all()
    )


def create_bookmark(
    db: Session, *, user_id: int, verse_key: str | None, page_number: int | None
) -> QuranBookmark:
    bookmark = QuranBookmark(
        user_id=user_id, verse_key=verse_key, page_number=page_number
    )
    db.add(bookmark)
    db.commit()
    db.refresh(bookmark)
    return bookmark


def delete_bookmark(db: Session, *, user_id: int, bookmark_id: int) -> bool:
    bookmark = db.get(QuranBookmark, bookmark_id)
    if bookmark is None or bookmark.user_id != user_id:
        return False
    db.delete(bookmark)
    db.commit()
    return True
