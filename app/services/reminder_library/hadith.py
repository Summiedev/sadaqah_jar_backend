"""Authentic hadith reminder content across many themes."""

from app.services.reminder_library.base import ReminderEntry

HADITH = [
    # Motivation & Sincerity
    ReminderEntry(
        "Actions are by intentions",
        "The Prophet ﷺ said: 'Actions are only by intentions, and every person will have only what they intended.' (Sahih al-Bukhari 1). Renew your intention before every act.",
        "hadith", "Sahih al-Bukhari 1", ("intention", "sincerity"),
    ),
    ReminderEntry(
        "Allah looks at your hearts",
        "The Prophet ﷺ said: 'Allah does not look at your bodies or your forms, but He looks at your hearts and your deeds.' (Sahih Muslim 2564). Beautify what is inside.",
        "hadith", "Sahih Muslim 2564", ("sincerity", "heart"),
    ),
    ReminderEntry(
        "The reward of the seeker",
        "The Prophet ﷺ said: 'Whoever travels a path seeking knowledge, Allah makes easy for him a path to Paradise.' (Sahih Muslim 2699).",
        "hadith", "Sahih Muslim 2699", ("knowledge", "motivation"),
    ),
    ReminderEntry(
        "No one who loves you more",
        "The Prophet ﷺ said: 'None of you truly believes until he loves for his brother what he loves for himself.' (Sahih al-Bukhari 13).",
        "hadith", "Sahih al-Bukhari 13", ("brotherhood", "character"),
    ),
    ReminderEntry(
        "The best of deeds",
        "The Prophet ﷺ was asked: 'Which deed is best?' He said: 'Faith in Allah and His Messenger, then prayer at its proper time, then kindness to parents.' (Sahih al-Bukhari 527).",
        "hadith", "Sahih al-Bukhari 527", ("deeds", "parents"),
    ),
    # Charity
    ReminderEntry(
        "Charity does not decrease wealth",
        "The Prophet ﷺ said: 'Charity does not decrease wealth.' (Sahih Muslim 2588). Give and watch your rizq expand in unseen ways.",
        "hadith", "Sahih Muslim 2588", ("charity", "sadaqah"),
    ),
    ReminderEntry(
        "Every good deed is charity",
        "The Prophet ﷺ said: 'Every good deed is charity. Smiling at your brother is charity; removing harm from the road is charity.' (Jami at-Tirmidhi 1970).",
        "hadith", "Jami at-Tirmidhi 1970", ("charity", "kindness", "smile"),
    ),
    ReminderEntry(
        "The sadaqah that extinguishes sins",
        "The Prophet ﷺ said: 'Sadaqah extinguishes sin as water extinguishes fire.' (Jami at-Tirmidhi 2616). Give today and purify your record.",
        "hadith", "Jami at-Tirmidhi 2616", ("charity", "purification"),
    ),
    ReminderEntry(
        "Give from the best of what you earn",
        "The Prophet ﷺ said: 'Allah is Good and accepts only what is good.' (Sahih Muslim 1015). Give charity from pure, halal wealth.",
        "hadith", "Sahih Muslim 1015", ("charity", "halal"),
    ),
    ReminderEntry(
        "The upper hand is better",
        "The Prophet ﷺ said: 'The upper hand is better than the lower hand. The upper hand gives, the lower hand receives.' (Sahih al-Bukhari 1427).",
        "hadith", "Sahih al-Bukhari 1427", ("charity", "giving"),
    ),
    # Gratitude
    ReminderEntry(
        "Gratitude for the little",
        "The Prophet ﷺ said: 'Whoever does not thank people has not thanked Allah.' (Jami at-Tirmidhi 1955). Say thank you today.",
        "hadith", "Jami at-Tirmidhi 1955", ("gratitude", "character"),
    ),
    ReminderEntry(
        "Count the blessings",
        "The Prophet ﷺ said: 'Look at those below you, not above you, for it is more fitting that you not underestimate the blessings of Allah.' (Sahih Muslim 2963).",
        "hadith", "Sahih Muslim 2963", ("gratitude", "contentment"),
    ),
    ReminderEntry(
        "A word that balances the scales",
        "The Prophet ﷺ said: 'Alhamdulillah fills the scales.' (Sahih Muslim 223). One phrase in gratitude equals infinite weight in His sight.",
        "hadith", "Sahih Muslim 223", ("gratitude", "dhikr"),
    ),
    # Patience
    ReminderEntry(
        "Amazing is the affair of the believer",
        "The Prophet ﷺ said: 'Amazing is the affair of the believer. All of it is good — if he is prosperous, he thanks; if he is afflicted, he is patient.' (Sahih Muslim 2999).",
        "hadith", "Sahih Muslim 2999", ("patience", "trust"),
    ),
    ReminderEntry(
        "The strong one",
        "The Prophet ﷺ said: 'The strong one is not the one who overcomes people — the strong one is the one who controls himself at the time of anger.' (Sahih al-Bukhari 6114).",
        "hadith", "Sahih al-Bukhari 6114", ("patience", "anger"),
    ),
    ReminderEntry(
        "Patience at the moment of shock",
        "The Prophet ﷺ said: 'Real patience is at the first stroke of a calamity.' (Sahih al-Bukhari 1302). Face trials with dignity and trust.",
        "hadith", "Sahih al-Bukhari 1302", ("patience", "trials"),
    ),
    # Repentance
    ReminderEntry(
        "Allah is more delighted than you can imagine",
        "The Prophet ﷺ said: 'Allah is more delighted with the repentance of His servant than a man who finds his lost camel in the desert.' (Sahih al-Bukhari 6309). Never despair.",
        "hadith", "Sahih al-Bukhari 6309", ("repentance", "mercy"),
    ),
    ReminderEntry(
        "He loves to forgive",
        "The Prophet ﷺ said: 'If you did not commit sins, Allah would wipe you out and bring people who commit sins, then ask for forgiveness, and He would forgive them.' (Sahih Muslim 2749).",
        "hadith", "Sahih Muslim 2749", ("repentance", "mercy"),
    ),
    ReminderEntry(
        "Seek forgiveness seventy times",
        "The Prophet ﷺ said: 'Whoever says Astaghfirullah, Allah will provide a way out of every distress and ease in every hardship.' (Sunan Abi Dawud 1518).",
        "hadith", "Sunan Abi Dawud 1518", ("repentance", "istighfar"),
    ),
    # Dhikr
    ReminderEntry(
        "Two phrases beloved to the Merciful",
        "The Prophet ﷺ said: 'Two phrases are light on the tongue, heavy on the scales: SubhanAllahi wa bihamdih, SubhanAllahil-'Adheem.' (Sahih al-Bukhari 6406).",
        "hadith", "Sahih al-Bukhari 6406", ("dhikr", "tasbih"),
    ),
    ReminderEntry(
        "Dhikr is a fortress",
        "The Prophet ﷺ said: 'The example of the one who remembers his Lord and the one who does not is like that of the living and the dead.' (Sahih al-Bukhari 6407).",
        "hadith", "Sahih al-Bukhari 6407", ("dhikr", "remembrance"),
    ),
    ReminderEntry(
        "The gardens of Paradise",
        "The Prophet ﷺ said: 'When you pass by the gardens of Paradise, graze therein.' They asked: 'What are the gardens of Paradise?' He said: 'The circles of dhikr.' (Jami at-Tirmidhi 3510).",
        "hadith", "Jami at-Tirmidhi 3510", ("dhikr", "gatherings"),
    ),
    # Prayer
    ReminderEntry(
        "The coolness of my eyes",
        "The Prophet ﷺ said: 'The coolness of my eyes was placed in prayer.' (Sunan an-Nasa'i 3940). Find your own coolness in it.",
        "hadith", "Sunan an-Nasa'i 3940", ("prayer", "love"),
    ),
    ReminderEntry(
        "The line between you and the Fire",
        "The Prophet ﷺ said: 'The first thing a servant will be asked about is prayer. If it is sound, the rest will be sound.' (Jami at-Tirmidhi 413).",
        "hadith", "Jami at-Tirmidhi 413", ("prayer", "accountability"),
    ),
    # Good character
    ReminderEntry(
        "The best of you",
        "The Prophet ﷺ said: 'The best of you are those with the best character.' (Sahih al-Bukhari 6035). Polish your manners today.",
        "hadith", "Sahih al-Bukhari 6035", ("character", "akhlaq"),
    ),
    ReminderEntry(
        "Smile is charity",
        "The Prophet ﷺ said: 'Your smile to your brother is charity.' (Jami at-Tirmidhi 1956). You can give sadaqah with a single smile.",
        "hadith", "Jami at-Tirmidhi 1956", ("smile", "charity"),
    ),
    ReminderEntry(
        "Removing harm is charity",
        "The Prophet ﷺ said: 'Removing harmful things from the road is charity.' (Sahih Muslim 1009). A single act of care counts.",
        "hadith", "Sahih Muslim 1009", ("harm", "charity"),
    ),
    # Family ties
    ReminderEntry(
        "The connection of kinship",
        "The Prophet ﷺ said: 'The one who severs ties of kinship will not enter Paradise.' (Sahih al-Bukhari 5984). Call a relative today.",
        "hadith", "Sahih al-Bukhari 5984", ("family", "ties"),
    ),
    ReminderEntry(
        "Kinship is suspended from the Throne",
        "The Prophet ﷺ said: 'Kinship is suspended from the Throne. Whoever connects it, Allah connects with him.' (Sahih al-Bukhari 5989).",
        "hadith", "Sahih al-Bukhari 5989", ("family", "ties"),
    ),
    # Dua
    ReminderEntry(
        "Dua is worship",
        "The Prophet ﷺ said: 'Dua is worship.' (Jami at-Tirmidhi 3371). Ask Allah boldly — He loves to be asked.",
        "hadith", "Jami at-Tirmidhi 3371", ("dua", "worship"),
    ),
    ReminderEntry(
        "You will be answered",
        "The Prophet ﷺ said: 'There is no Muslim who calls upon Allah with a supplication free from sin and cutting ties, but Allah will give him one of three: His request, store it for him, or repel an evil from him.' (Musnad Ahmad 11133).",
        "hadith", "Musnad Ahmad 11133", ("dua", "hope"),
    ),
    # Mercy & kindness
    ReminderEntry(
        "Be merciful, you will be shown mercy",
        "The Prophet ﷺ said: 'Those who are merciful will be shown mercy by the Most Merciful. Be merciful to those on earth, and the One above the heavens will be merciful to you.' (Jami at-Tirmidhi 1924).",
        "hadith", "Jami at-Tirmidhi 1924", ("mercy", "kindness"),
    ),
    ReminderEntry(
        "The believer is gentle",
        "The Prophet ﷺ said: 'The believer is not the one who curses or slanders.' (Jami at-Tirmidhi 1977). Choose gentle words today.",
        "hadith", "Jami at-Tirmidhi 1977", ("character", "gentleness"),
    ),
]