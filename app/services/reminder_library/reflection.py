"""Reflection prompt and journaling reminder content."""

from app.services.reminder_library.base import ReminderEntry

REFLECTION = [
    ReminderEntry(
        "Reflect on your day",
        "Before you sleep, ask yourself: What did I do today that Allah would love? What would I do differently tomorrow? Write it down.",
        "reflection",
        "",
        ("journaling",),
    ),
    ReminderEntry(
        "Three blessings",
        "Name three blessings from today — however small. Gratitude journaling rewires the heart toward contentment.",
        "reflection",
        "",
        ("journaling", "gratitude"),
    ),
    ReminderEntry(
        "The state of your heart",
        "Check your heart: Is it connected to Allah, or distracted by the world? One honest reflection is the beginning of change.",
        "reflection",
        "",
        ("journaling", "heart"),
    ),
    ReminderEntry(
        "What touched you recently?",
        "Think of a verse or moment that moved you this week. Why did it touch you? Write it down and reflect on its meaning in your life.",
        "reflection",
        "",
        ("journaling", "quran"),
    ),
    ReminderEntry(
        "A person you admire",
        "Think of someone whose character you admire. What is one quality of theirs you can practice today?",
        "reflection",
        "",
        ("journaling", "character"),
    ),
    ReminderEntry(
        "Where would you change?",
        "If you could change one habit to draw closer to Allah, what would it be? Small steps repeated beat grand intentions abandoned.",
        "reflection",
        "",
        ("journaling", "improvement"),
    ),
    ReminderEntry(
        "Your thoughts on patience",
        "Recall a trial you endured patiently. How did Allah reward you from it afterward? Carry that memory as proof of His promise.",
        "reflection",
        "",
        ("journaling", "patience"),
    ),
    ReminderEntry(
        "The people you love",
        "Who are the people you love for the sake of Allah? Have you told them? A word of love is charity.",
        "reflection",
        "",
        ("journaling", "love"),
    ),
    ReminderEntry(
        "Journal your gratitude",
        "The Prophet ﷺ said gratitude increases blessings. Write down five things you are grateful for today.",
        "reflection",
        "",
        ("journaling", "gratitude"),
    ),
    ReminderEntry(
        "The Qur'an is speaking to you",
        "When you read the Qur'an, ask: 'What is this verse telling me right now?' The Qur'an is always relevant — let it answer your current struggle.",
        "reflection",
        "",
        ("journaling", "quran"),
    ),
]
