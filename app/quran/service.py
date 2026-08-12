from __future__ import annotations

from sqlalchemy.orm import Session

from app.quran import repository as repo
from app.quran.models import QuranAyah, QuranSurah
from app.quran.schemas import (
    QuranArabicResponse,
    QuranAudioResponse,
    QuranAyahResponse,
    QuranBookmarkResponse,
    QuranMetaResponse,
    QuranPageResponse,
    QuranSearchResult,
    QuranSurahResponse,
    QuranTranslationResponse,
)


DEFAULT_TRANSLATION = "en.hilali-khan"


def _ayah_response(
    ayah: QuranAyah, translation_code: str = DEFAULT_TRANSLATION
) -> QuranAyahResponse:
    translation = next(
        (item for item in ayah.translations if item.edition_code == translation_code),
        ayah.translations[0] if ayah.translations else None,
    )
    return QuranAyahResponse(
        verse_key=ayah.verse_key,
        surah_id=ayah.surah_id,
        ayah_number=ayah.ayah_number,
        arabic=QuranArabicResponse(
            uthmani=ayah.text_uthmani,
            tajweed=ayah.text_uthmani_tajweed,
            simple=ayah.text_simple,
        ),
        translation=(
            QuranTranslationResponse(
                edition=translation.edition_code,
                language=translation.language,
                translator_name=translation.translator_name,
                text=translation.text,
            )
            if translation
            else None
        ),
        transliteration=ayah.transliteration.text if ayah.transliteration else None,
        audio=[
            QuranAudioResponse(
                reciter_id=audio.reciter_id,
                url=audio.url,
                start_ms=audio.start_ms,
                end_ms=audio.end_ms,
            )
            for audio in ayah.audio_segments
        ],
        meta=QuranMetaResponse(
            juz=ayah.juz_number,
            hizb=ayah.hizb_number,
            hizb_quarter=ayah.hizb_quarter,
            manzil=ayah.manzil_number,
            ruku=ayah.ruku_number,
            page=ayah.page_number,
            sajda=ayah.sajda,
            sajda_type=ayah.sajda_type,
        ),
    )


def _surah_response(db: Session, surah: QuranSurah) -> QuranSurahResponse:
    ayahs = repo.ayahs_for_surah(db, surah.id)
    return QuranSurahResponse(
        id=surah.id,
        name_ar=surah.name_ar,
        name_en=surah.name_en,
        name_transliteration=surah.name_transliteration,
        revelation_type=surah.revelation_type,
        ayah_count=surah.ayah_count,
        bismillah_pre=surah.bismillah_pre,
        first_page=ayahs[0].page_number if ayahs else None,
        last_page=ayahs[-1].page_number if ayahs else None,
        first_juz=ayahs[0].juz_number if ayahs else None,
    )


def list_surahs(db: Session) -> list[QuranSurahResponse]:
    return [_surah_response(db, surah) for surah in repo.list_surahs(db)]


def get_surah_ayahs(db: Session, surah_id: int) -> list[QuranAyahResponse]:
    return [_ayah_response(ayah) for ayah in repo.ayahs_for_surah(db, surah_id)]


def get_page(db: Session, page_number: int) -> QuranPageResponse:
    asset = repo.get_page_asset(db, page_number)
    ayahs = repo.ayahs_for_page(db, page_number)
    return QuranPageResponse(
        page_number=page_number,
        image_url=asset.image_url if asset else None,
        local_storage_key=asset.local_storage_key if asset else None,
        ayahs=[_ayah_response(ayah) for ayah in ayahs],
    )


def get_juz(db: Session, juz_number: int) -> list[QuranAyahResponse]:
    return [_ayah_response(ayah) for ayah in repo.ayahs_for_juz(db, juz_number)]


def get_hizb(db: Session, hizb_number: int) -> list[QuranAyahResponse]:
    return [_ayah_response(ayah) for ayah in repo.ayahs_for_hizb(db, hizb_number)]


def search(db: Session, query: str, limit: int) -> list[QuranSearchResult]:
    ayahs = repo.search(db, query.strip(), limit)
    results = []
    for ayah in ayahs:
        translation = ayah.translations[0].text if ayah.translations else None
        results.append(
            QuranSearchResult(
                verse_key=ayah.verse_key,
                surah_id=ayah.surah_id,
                ayah_number=ayah.ayah_number,
                page_number=ayah.page_number,
                surah_name=ayah.surah.name_transliteration if ayah.surah else "",
                text=ayah.text_uthmani,
                translation=translation,
            )
        )
    return results


def list_bookmarks(db: Session, user_id: int) -> list[QuranBookmarkResponse]:
    return [
        QuranBookmarkResponse(
            id=bookmark.id,
            verse_key=bookmark.verse_key,
            page_number=bookmark.page_number,
        )
        for bookmark in repo.list_bookmarks(db, user_id)
    ]


def create_bookmark(
    db: Session, *, user_id: int, verse_key: str | None, page_number: int | None
) -> QuranBookmarkResponse:
    bookmark = repo.create_bookmark(
        db, user_id=user_id, verse_key=verse_key, page_number=page_number
    )
    return QuranBookmarkResponse(
        id=bookmark.id,
        verse_key=bookmark.verse_key,
        page_number=bookmark.page_number,
    )


def delete_bookmark(db: Session, *, user_id: int, bookmark_id: int) -> bool:
    return repo.delete_bookmark(db, user_id=user_id, bookmark_id=bookmark_id)
