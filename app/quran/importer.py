"""Import Quran Foundation content into Mizan's local Quran tables.

Run with::

    python -m app.quran.importer

The importer is deliberately backend-only. It discovers the configured
Hilali/Khan translation and Ibn Kathir resources by name, then imports the
604-page QCF V2 Mushaf in small transactions so a dropped connection can be
re-run without duplicating rows.
"""

from __future__ import annotations

import argparse
import logging
import os
from typing import Any

import httpx

from app.core.config import settings
from app.db.session import SessionLocal
from app.quran.models import (
    QuranAudioSegment,
    QuranAyah,
    QuranPageAsset,
    QuranTranslation,
    QuranTransliteration,
)

logger = logging.getLogger(__name__)

API_BASES = {
    "production": "https://apis.quran.foundation",
    "prelive": "https://apis-prelive.quran.foundation",
}
OAUTH_BASES = {
    "production": "https://oauth2.quran.foundation",
    "prelive": "https://prelive-oauth2.quran.foundation",
}
MUSHAF_ID = 1  # QCF V2, the standard 604-page Madinah Mushaf.
TRANSLATION_CODE = "en.hilali-khan"
TAFSIR_CODE = "tafsir.ibn-kathir"
RECITER_ID = "7"  # Mishary Rashid Alafasy, ayah-by-ayah audio.


class QuranImportError(RuntimeError):
    """Raised when the remote dataset is incomplete or inaccessible."""


class QuranFoundationClient:
    def __init__(self) -> None:
        env = settings.QF_ENV.lower()
        if env not in API_BASES:
            raise QuranImportError("QF_ENV must be production or prelive")
        if not settings.QF_CLIENT_ID or not settings.QF_CLIENT_SECRET:
            raise QuranImportError(
                "QF_CLIENT_ID and QF_CLIENT_SECRET must be set in the backend .env"
            )
        self.client_id = settings.QF_CLIENT_ID
        self.http = httpx.Client(timeout=60.0)
        self.base = API_BASES[env]
        self.oauth = OAUTH_BASES[env]
        response = self.http.post(
            f"{self.oauth}/oauth2/token",
            auth=(settings.QF_CLIENT_ID, settings.QF_CLIENT_SECRET),
            data={"grant_type": "client_credentials", "scope": "content"},
        )
        response.raise_for_status()
        token = response.json().get("access_token")
        if not token:
            raise QuranImportError("Quran Foundation returned no access token")
        self.headers = {"x-auth-token": token, "x-client-id": self.client_id}

    def get(self, path: str, **params: Any) -> dict[str, Any]:
        response = self.http.get(
            f"{self.base}/content/api/v4/{path.lstrip('/')}",
            headers=self.headers,
            params={key: value for key, value in params.items() if value is not None},
        )
        if response.status_code >= 400:
            raise QuranImportError(
                f"Quran Foundation {response.status_code} for {path}: "
                f"{response.text[:400]}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise QuranImportError(f"Unexpected response from {path}")
        return payload


def _items(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    return [dict(item) for item in value if isinstance(item, dict)]


def _resource_id(resources: list[dict[str, Any]], *needles: str) -> int:
    for resource in resources:
        name = str(
            resource.get("name")
            or resource.get("resource_name")
            or resource.get("slug")
            or ""
        ).lower()
        if all(needle in name for needle in needles):
            resource_id = resource.get("id") or resource.get("resource_id")
            if resource_id is not None:
                return int(resource_id)
    raise QuranImportError(
        f"Could not find a resource containing: {', '.join(needles)}"
    )


def _page(value: Any, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _translation(verse: dict[str, Any], resource_id: int) -> dict[str, Any] | None:
    for item in _items(verse, "translations"):
        if _page(item.get("resource_id"), -1) == resource_id:
            return item
    return None


def _tafsir(verse: dict[str, Any], resource_id: int) -> dict[str, Any] | None:
    for item in _items(verse, "tafsirs"):
        if _page(item.get("resource_id"), -1) == resource_id:
            return item
    return None


def import_dataset(*, dry_run: bool = False) -> None:
    client = QuranFoundationClient()
    chapters = _items(client.get("chapters"), "chapters")
    if len(chapters) != 114:
        raise QuranImportError(f"Expected 114 chapters, received {len(chapters)}")
    translations = _items(client.get("resources/translations"), "translations")
    tafsirs = _items(client.get("resources/tafsirs"), "tafsirs")
    translation_id = _resource_id(translations, "hilali", "khan")
    tafsir_id = _resource_id(tafsirs, "ibn", "kathir")
    logger.info("Using translation=%s tafsir=%s", translation_id, tafsir_id)
    if dry_run:
        return

    db = SessionLocal()
    try:
        for page_number in range(1, 605):
            payload = client.get(
                f"verses/by_page/{page_number}",
                mushaf=MUSHAF_ID,
                words="true",
                word_fields="text_uthmani,text_qpc_hafs,page_number,line_number",
                translations=translation_id,
                tafsirs=tafsir_id,
                audio=RECITER_ID,
            )
            verses = _items(payload, "verses")
            if not verses:
                raise QuranImportError(f"No verses returned for Mushaf page {page_number}")
            for verse in verses:
                key = str(verse.get("verse_key") or "")
                if ":" not in key:
                    raise QuranImportError(f"Invalid verse key on page {page_number}: {key}")
                surah_id, ayah_number = (int(part) for part in key.split(":", 1))
                meta = verse
                existing = db.query(QuranAyah).filter_by(verse_key=key).one_or_none()
                if existing is None:
                    existing = QuranAyah(verse_key=key, surah_id=surah_id, ayah_number=ayah_number)
                    db.add(existing)
                existing.text_uthmani = str(verse.get("text_uthmani") or "")
                existing.text_uthmani_tajweed = verse.get("text_uthmani_tajweed")
                existing.text_simple = verse.get("text_imlaei_simple") or verse.get("text_simple")
                existing.juz_number = _page(meta.get("juz_number"), 1)
                existing.hizb_number = _page(meta.get("hizb_number"), 1)
                existing.hizb_quarter = meta.get("rub_el_hizb_number")
                existing.manzil_number = meta.get("manzil_number")
                existing.ruku_number = meta.get("ruku_number")
                existing.page_number = _page(meta.get("page_number"), page_number)
                existing.sajda = bool(meta.get("sajda") or False)
                existing.sajda_type = meta.get("sajda_type")
                db.flush()
                db.query(QuranTranslation).filter_by(ayah_id=existing.id).delete()
                db.query(QuranTransliteration).filter_by(ayah_id=existing.id).delete()
                db.query(QuranAudioSegment).filter_by(ayah_id=existing.id).delete()
                translation = _translation(verse, translation_id)
                if translation:
                    db.add(QuranTranslation(
                        ayah_id=existing.id,
                        edition_code=TRANSLATION_CODE,
                        language="en",
                        translator_name="Muhammad Taqi-ud-Din al-Hilali and Muhammad Muhsin Khan",
                        text=str(translation.get("text") or ""),
                    ))
                tafsir = _tafsir(verse, tafsir_id)
                if tafsir:
                    # The current schema predates a dedicated tafsir table.
                    # Keep the verified tafsir in the same ayah-linked content
                    # table under a distinct edition code until that API field
                    # is exposed separately.
                    db.add(QuranTranslation(
                        ayah_id=existing.id,
                        edition_code=TAFSIR_CODE,
                        language="en",
                        translator_name="Abridged Tafsir Ibn Kathir",
                        text=str(tafsir.get("text") or ""),
                    ))
                transliteration = verse.get("transliteration")
                if isinstance(transliteration, dict) and transliteration.get("text"):
                    db.add(QuranTransliteration(ayah_id=existing.id, text=str(transliteration["text"])))
                audio = verse.get("audio")
                for item in _items({"items": audio}, "items"):
                    if item.get("url"):
                        db.add(QuranAudioSegment(
                            ayah_id=existing.id,
                            reciter_id=str(item.get("reciter_id") or RECITER_ID),
                            url=str(item["url"]),
                            start_ms=item.get("start_ms"),
                            end_ms=item.get("end_ms"),
                        ))
                image_url = verse.get("image_url")
                if image_url:
                    db.merge(QuranPageAsset(
                        page_number=page_number,
                        image_url=(
                            f"https:{image_url}" if str(image_url).startswith("//") else str(image_url)
                        ),
                        local_storage_key=f"quran/mushaf-qcf-v2/{page_number}.png",
                        width=verse.get("image_width"),
                        height=verse.get("image_height"),
                        source="quran.foundation:qcf-v2",
                    ))
            db.commit()
            if page_number % 10 == 0:
                logger.info("Imported Mushaf page %s/604", page_number)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
        client.http.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Verify credentials and resources only")
    args = parser.parse_args()
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    import_dataset(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
