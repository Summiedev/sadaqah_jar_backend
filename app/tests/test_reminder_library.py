"""Tests for the expanded reminder content library."""

from app.services.reminder_library import (
    LIBRARY,
    SOURCE_TO_CATEGORY,
    TOTAL_ENTRIES,
    get_entries_for_source,
    get_entry_count,
    get_random_entry,
)


class TestReminderLibrary:
    def test_library_has_all_categories(self):
        expected = {
            "prayer_fardh",
            "prayer_nafl",
            "adhkar_morning",
            "adhkar_evening",
            "time_based",
            "quran",
            "hadith",
            "reflection",
            "hereafter",
            "good_deeds",
            "quotes",
        }
        assert set(LIBRARY.keys()) == expected

    def test_library_is_large(self):
        assert TOTAL_ENTRIES >= 100

    def test_each_category_has_entries(self):
        for category, entries in LIBRARY.items():
            assert len(entries) > 0, f"Category {category} is empty"

    def test_entries_have_required_fields(self):
        for category, entries in LIBRARY.items():
            for entry in entries:
                assert entry.title, f"Empty title in {category}"
                assert entry.message, f"Empty message in {category}"
                assert entry.category == category

    def test_source_mapping(self):
        assert SOURCE_TO_CATEGORY["prayer_fardh"] == "prayer_fardh"
        assert SOURCE_TO_CATEGORY["quran_ayah"] == "quran"
        assert SOURCE_TO_CATEGORY["reflection_prompt"] == "reflection"

    def test_get_entries_for_source(self):
        entries = get_entries_for_source("hadith")
        assert len(entries) > 0
        assert entries[0].category == "hadith"

    def test_get_entry_count(self):
        assert get_entry_count("quran") == len(LIBRARY["quran"])
        assert get_entry_count("unknown_source") == 0

    def test_get_random_entry(self):
        entry = get_random_entry("hadith")
        assert entry is not None
        assert entry.category == "hadith"

    def test_get_random_entry_unknown_source(self):
        assert get_random_entry("unknown_source") is None

    def test_get_random_entry_excludes(self):
        entries = get_entries_for_source("quran")
        if len(entries) > 1:
            entry = get_random_entry("quran", exclude={0})
            assert entry is not None
            assert entry != entries[0]
