"""Morning adhkar reminder content."""

from app.services.reminder_library.base import ReminderEntry

ADHKAR_MORNING = [
    ReminderEntry(
        "Morning protection",
        "Recite Ayat al-Kursi in the morning and you will be protected until the evening. (Sahih al-Bukhari 2311). Begin your day under divine safeguard.",
        "adhkar_morning", "Sahih al-Bukhari 2311", ("morning", "adhkar"),
    ),
    ReminderEntry(
        "Start with His name",
        "Whoever says 'Bismillah' in the morning, nothing will harm him. (Jami at-Tirmidhi 3388). Begin your day with the name of Allah.",
        "adhkar_morning", "Jami at-Tirmidhi 3388", ("morning", "adhkar"),
    ),
    ReminderEntry(
        "The morning tasbih",
        "Say 'SubhanAllahi wa bihamdih' 100 times in the morning — your sins will be forgiven even if they were like the foam of the sea. (Sahih al-Bukhari 6405).",
        "adhkar_morning", "Sahih al-Bukhari 6405", ("morning", "tasbih"),
    ),
    ReminderEntry(
        "A morning fortress",
        "The Prophet ﷺ taught us to seek refuge with the Perfect Words of Allah in the morning — nothing will harm you after that. (Sahih Muslim).",
        "adhkar_morning", "Sahih Muslim 2708", ("morning", "protection"),
    ),
    ReminderEntry(
        "Thank God for the day",
        "Begin your morning with 'Alhamdulillah' — gratitude opens the doors of more blessings.",
        "adhkar_morning", "", ("morning", "gratitude"),
    ),
    ReminderEntry(
        "The morning light of dhikr",
        "The Prophet ﷺ said: 'The best words after the Quran are: SubhanAllah, Alhamdulillah, Allahu Akbar, La ilaha illallah.' (Sunan an-Nasa'i). Start your day with them.",
        "adhkar_morning", "Sunan an-Nasa'i 9259", ("morning", "dhikr"),
    ),
]