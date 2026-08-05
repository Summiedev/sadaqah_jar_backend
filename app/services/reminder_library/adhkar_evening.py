"""Evening adhkar reminder content."""

from app.services.reminder_library.base import ReminderEntry

ADHKAR_EVENING = [
    ReminderEntry(
        "Evening remembrance",
        "The Prophet ﷺ said whoever says in the evening 'A'udhu bi kalimatillahi't-tammati min sharri ma khalaq' three times, nothing will harm him that night. (Sahih Muslim).",
        "adhkar_evening", "Sahih Muslim 2709", ("evening", "adhkar"),
    ),
    ReminderEntry(
        "Close the day with dhikr",
        "Say 'Astaghfirullah' as the day ends — the Prophet ﷺ sought forgiveness from Allah more than seventy times a day. (Sahih al-Bukhari 6307).",
        "adhkar_evening", "Sahih al-Bukhari 6307", ("evening", "istighfar"),
    ),
    ReminderEntry(
        "The evening tasbih",
        "SubhanAllahi wa bihamdih in the evening — a phrase heavy on the scales and beloved to the Most Merciful. (Sahih al-Bukhari 6405).",
        "adhkar_evening", "Sahih al-Bukhari 6405", ("evening", "tasbih"),
    ),
    ReminderEntry(
        "Before the night settles",
        "The night angels take your deeds to Allah. Let your last words be dhikr, so your record ends beautifully.",
        "adhkar_evening", "", ("evening", "dhikr"),
    ),
    ReminderEntry(
        "Evening protection",
        "Recite the last two ayahs of Surah al-Baqarah at night and they will suffice you. (Sahih al-Bukhari 5009). Protect your night with them.",
        "adhkar_evening", "Sahih al-Bukhari 5009", ("evening", "protection"),
    ),
    ReminderEntry(
        "A quiet evening with Allah",
        "The minutes before Maghrib are precious. Spend them in istighfar and let the sunset find you in remembrance.",
        "adhkar_evening", "", ("evening", "maghrib"),
    ),
]