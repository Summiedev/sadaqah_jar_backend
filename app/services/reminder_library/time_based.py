"""Time-based reminder content (Friday, fasting, Ramadan, night)."""

from app.services.reminder_library.base import ReminderEntry

TIME_BASED = [
    ReminderEntry(
        "Friday — the best day",
        "The Prophet ﷺ said Friday is the best day on which the sun has ever risen. (Sahih Muslim). Make it special.",
        "time_based",
        "Sahih Muslim 854",
        ("friday",),
    ),
    ReminderEntry(
        "Send salawat on Friday",
        "The Prophet ﷺ said: 'Send abundant salawat upon me on Friday — your salawat are presented to me.' (Sunan Abi Dawud).",
        "time_based",
        "Sunan Abi Dawud 1047",
        ("friday", "salawat"),
    ),
    ReminderEntry(
        "Surah Al-Kahf is a light",
        "Whoever recites Surah Al-Kahf on Friday, a light will shine for him between the two Fridays. (Sunan al-Kubra al-Bayhaqi).",
        "time_based",
        "Al-Bayhaqi 6010",
        ("friday", "kahf"),
    ),
    ReminderEntry(
        "The hour of acceptance",
        "There is an hour on Friday when no Muslim asks Allah for something but He gives it. (Sahih al-Bukhari 935). Seek it after Asr.",
        "time_based",
        "Sahih al-Bukhari 935",
        ("friday", "dua"),
    ),
    ReminderEntry(
        "The last third of the night",
        "The Prophet ﷺ said our Lord descends to the lowest heaven in the last third of the night and says: 'Who will ask Me, so that I may give him?' (Sahih al-Bukhari). Wake up.",
        "time_based",
        "Sahih al-Bukhari 1145",
        ("night", "tahajjud", "dua"),
    ),
    ReminderEntry(
        "The fasting day",
        "Whoever fasts a day for the sake of Allah, Allah will distance his face from the Fire by seventy autumns. (Sahih Muslim). Consider a voluntary fast.",
        "time_based",
        "Sahih Muslim 1153",
        ("fasting",),
    ),
    ReminderEntry(
        "Fasting Monday and Thursday",
        "The Prophet ﷺ used to fast Mondays and Thursdays — the days when deeds are presented to Allah. (Jami at-Tirmidhi 747).",
        "time_based",
        "Jami at-Tirmidhi 747",
        ("fasting",),
    ),
    ReminderEntry(
        "The white days",
        "Fast the 13th, 14th, and 15th of the Islamic month — the white days — and receive the reward of fasting the whole month. (Sunan an-Nasa'i).",
        "time_based",
        "Sunan an-Nasa'i 2419",
        ("fasting",),
    ),
    ReminderEntry(
        "A Ramadan mindset",
        "In Ramadan, the gates of Paradise are opened and the gates of Hell are closed. (Sahih al-Bukhari). Carry that spirit into every month.",
        "time_based",
        "Sahih al-Bukhari 1899",
        ("ramadan",),
    ),
    ReminderEntry(
        "The night of power",
        "The Night of Decree is better than a thousand months. (Quran 97:3). Seek it with devotion in the last ten nights.",
        "time_based",
        "Quran 97:3",
        ("ramadan", "laylatul_qadr"),
    ),
    ReminderEntry(
        "Ramadan is a gift",
        "Ramadan has arrived — a month of mercy, forgiveness, and freedom from the Fire. (Sahih Muslim). Enter it with a pure heart.",
        "time_based",
        "Sahih Muslim 1079",
        ("ramadan",),
    ),
    ReminderEntry(
        "The day of Arafah",
        "Fasting the day of Arafah expiates the sins of the past and coming year. (Sahih Muslim 1162). A day of immense reward.",
        "time_based",
        "Sahih Muslim 1162",
        ("fasting", "arafah"),
    ),
    ReminderEntry(
        "The day of Ashura",
        "Fasting Ashura expiates the sins of the past year. (Sahih Muslim 1162). A day of gratitude and remembrance.",
        "time_based",
        "Sahih Muslim 1162",
        ("fasting", "ashura"),
    ),
]
