"""Hereafter, death, accountability, Jannah, and preparation reminder content."""

from app.services.reminder_library.base import ReminderEntry

HEREAFTER = [
    ReminderEntry(
        "Remember the destroyer of pleasures",
        "The Prophet ﷺ said: 'Remember often the destroyer of pleasures — death.' (Jami at-Tirmidhi 2307). Not to despair, but to live intentionally.",
        "hereafter",
        "Jami at-Tirmidhi 2307",
        ("death", "accountability"),
    ),
    ReminderEntry(
        "The grave is the first station",
        "The Prophet ﷺ said: 'The grave is the first stage of the Hereafter. If one is saved from it, what follows is easier; if not, what follows is harder.' (Jami at-Tirmidhi 2308). Prepare now.",
        "hereafter",
        "Jami at-Tirmidhi 2308",
        ("grave", "hereafter"),
    ),
    ReminderEntry(
        "The scales are waiting",
        "Whatever you do today is weighed. The Prophet ﷺ said: 'Two words are light on the tongue, heavy on the scales.' (Sahih al-Bukhari 6406). Fill your scales with good.",
        "hereafter",
        "Sahih al-Bukhari 6406",
        ("scales", "accountability"),
    ),
    ReminderEntry(
        "What have you prepared?",
        "The Prophet ﷺ said: 'What have I prepared for it?' when asked about the Hereafter. (Sahih al-Bukhari 6024). Ask yourself the same.",
        "hereafter",
        "Sahih al-Bukhari 6024",
        ("preparation", "accountability"),
    ),
    ReminderEntry(
        "The path to Jannah is paved with trials",
        "The Prophet ﷺ said: 'Paradise is surrounded by hardships, and the Fire is surrounded by desires.' (Sahih Muslim 2822). Choose the harder path today.",
        "hereafter",
        "Sahih Muslim 2822",
        ("jannah", "trials"),
    ),
    ReminderEntry(
        "A glimpse of Jannah",
        "The Prophet ﷺ said: 'In Paradise, there is what no eye has seen, no ear has heard, and no heart has conceived.' (Sahih Muslim 2824). Work for it.",
        "hereafter",
        "Sahih Muslim 2824",
        ("jannah", "hope"),
    ),
    ReminderEntry(
        "Whoever believes in Allah and the Last Day",
        "The Prophet ﷺ said: 'Whoever believes in Allah and the Last Day, let him speak good or remain silent.' (Sahih al-Bukhari 6018). Choose your words carefully.",
        "hereafter",
        "Sahih al-Bukhari 6018",
        ("accountability", "speech"),
    ),
    ReminderEntry(
        "The Day nothing is hidden",
        "On that Day, 'You will be shown all that you have done — even an atom's weight of good or evil.' (Quran 99:7-8). No detail is lost.",
        "hereafter",
        "Quran 99:7-8",
        ("accountability", "deeds"),
    ),
    ReminderEntry(
        "Grace beyond your deeds",
        "No one enters Paradise by his deeds alone — the Prophet ﷺ said: 'Not even I, except that Allah envelops me in His mercy.' (Sahih Muslim 2816). Hope for His mercy as you strive.",
        "hereafter",
        "Sahih Muslim 2816",
        ("mercy", "jannah"),
    ),
    ReminderEntry(
        "Save yourself from the Fire",
        "The Prophet ﷺ said: 'Protect yourselves from the Fire, even with half a date given in charity.' (Sahih al-Bukhari 1417). Small deeds count.",
        "hereafter",
        "Sahih al-Bukhari 1417",
        ("fire", "charity"),
    ),
]
