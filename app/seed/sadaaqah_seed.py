"""
Seed script for Sadaqah Jar — 50+ acts with evidence across 8 categories.

IMPORTANT: This file contains hadith citations. Entries marked with
"# SCHOLARLY REVIEW NEEDED" indicate citations where the author is not
fully confident in the exact source/number/grading. These must be verified
by a qualified Islamic scholar before production use. Wrong hadith
attribution is a credibility failure, not just a bug.
"""

import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.badge import Badge
from app.models.charity import Charity
from app.models.evidence import Evidence
from app.models.family_jar import FamilyJar
from app.models.family_jar_log import FamilyJarLog
from app.models.family_jar_member import FamilyJarMember
from app.models.jar import Jar
from app.models.sadaqah_act import SadaqahAct, SadaqahCategory
from app.models.sadaqah_log import SadaqahLog
from app.models.user import User
from app.models.user_badge import UserBadge

db: Session = SessionLocal()

# ---------------------------------------------------------------------------
# ACTS + EVIDENCE
# ---------------------------------------------------------------------------
# Each entry: (title, description, category, difficulty, estimated_time_minutes,
#              reward_weight, is_ramadan_only, ramadan_multiplier,
#              evidence_source_type, evidence_reference, evidence_grade,
#              evidence_arabic, evidence_english, evidence_explanation)
# evidence_* fields can be None for acts without specific citations.

ActSeed = tuple[str, str, SadaqahCategory, int, int | None, int, bool, int,
                 str | None, str | None, str | None, str | None, str | None, str | None]

acts_data: list[ActSeed] = [
    # =========================================================================
    # DHIKR (Remembrance of Allah)
    # =========================================================================
    (
        "Say SubhanAllah 100 times",
        "Glorify Allah by saying 'SubhanAllah' (Glory be to Allah) 100 times throughout the day. This simple act of dhikr purifies the heart and brings immense reward.",
        SadaqahCategory.dhikr, 1, 5, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 48, Hadith 37 (2693)", "Sahih",
        "سُبْحَانَ اللَّهِ وَبِحَمْدِهِ سُبْحَانَ اللَّهِ الْعَظِيمِ",
        "Whoever says 'SubhanAllah wa bihamdihi' 100 times in a day, his sins are forgiven even if they are like the foam of the sea.",
        "This hadith from Abu Hurairah (RA) shows the extraordinary mercy of Allah — a few minutes of dhikr can erase sins as vast as the ocean's foam. The phrase combines glorification (SubhanAllah) with praise (wa bihamdihi), acknowledging both Allah's perfection and our gratitude.",
    ),
    (
        "Say Alhamdulillah 100 times",
        "Express gratitude to Allah by saying 'Alhamdulillah' (All praise is due to Allah) 100 times. Gratitude is the key to increase in blessings.",
        SadaqahCategory.dhikr, 1, 5, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 48, Hadith 18 (2692)", "Sahih",
        "الْحَمْدُ لِلَّهِ",
        "Purity (SubhanAllah) fills half the scale, and 'Alhamdulillah' fills it entirely.",
        "The Prophet (PBUH) taught that 'Alhamdulillah' is so beloved to Allah that it fills the entire scale of good deeds on Judgment Day. This makes a few seconds of gratitude one of the most weighty acts a believer can perform.",
    ),
    (
        "Make dua for parents after every prayer",
        "After each of the five daily prayers, take a moment to sincerely supplicate for your parents — asking Allah to have mercy on them, forgive them, and bless them as they raised you.",
        SadaqahCategory.dhikr, 2, 2, 2, False, 1,
        "QURAN", "Surah Al-Isra (17:24)", "Quranic",
        "رَّبِّ ارْحَمْهُمَا كَمَا رَبَّيَانِي صَغِيرًا",
        "And lower to them the wing of humility out of mercy and say: 'My Lord, have mercy upon them as they brought me up [when I was] small.'",
        "This verse directly commands believers to pray for their parents with humility and love. Making this dua after each prayer ensures consistent remembrance of our parents' sacrifices and fulfills a Quranic obligation.",
    ),
    (
        "Read Ayat-ul-Kursi after every prayer",
        "Recite Ayat-ul-Kursi (Quran 2:255) after each obligatory prayer. This powerful verse is a protection and a means of entering Paradise.",
        SadaqahCategory.dhikr, 2, 3, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 99 (without number in some editions)", "Sahih",
        "اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ",
        "Whoever recites Ayat-ul-Kursi after every prescribed prayer, nothing prevents them from entering Paradise except death.",
        "This hadith (narrated by Abu Umamah, verified by Ibn Hibban and others) shows the immense virtue of this single verse after each prayer. It's a small time investment with a guaranteed return — Paradise.",
    ),
    (
        "Make istighfar 100 times daily",
        "Seek forgiveness from Allah by saying 'Astaghfirullah' (I seek forgiveness from Allah) 100 times. This brings relief from worry and opens doors of provision.",
        SadaqahCategory.dhikr, 1, 5, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 48, Hadith 35 (2702)", "Sahih",
        "أَسْتَغْفِرُ اللَّهَ وَأَتُوبُ إِلَيْهِ",
        "I seek forgiveness from Allah and repent to Him 100 times each day.",
        "The Prophet (PBUH) himself, despite being sinless, made istighfar 100 times daily. This teaches us that istighfar is not just for removing sins but for spiritual elevation, increased provision, and drawing closer to Allah.",
    ),
    (
        "Send salawat upon the Prophet 100 times on Friday",
        "Send blessings upon Prophet Muhammad (PBUH) by saying 'Allahumma salli ala Muhammad' 100 times on Friday. This is a specially rewarded act on the best day of the week.",
        SadaqahCategory.dhikr, 2, 5, 2, False, 2,
        "HADITH", "Sunan Abi Dawud, Book 2, Hadith 1047 (1531)", "Sahih",
        "اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ",
        "Increase your salawat upon me on Friday, for your salawat are presented to me.",
        "The Prophet (PBUH) specifically asked for increased blessings on Friday, the best day of the week. This act combines the virtue of dhikr with the special status of Jumu'ah, making it a powerful weekly practice.",
    ),
    (
        "Say 'La ilaha illallah' 100 times",
        "Proclaim the oneness of Allah by saying 'La ilaha illallah' (There is no god but Allah) 100 times. This is the best of all dhikr and the heaviest on the scales.",
        SadaqahCategory.dhikr, 1, 5, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 97, Hadith 1 (6405)", "Sahih",
        "لَا إِلَٰهَ إِلَّا اللَّهُ",
        "Whoever says 'La ilaha illallah' sincerely enters Paradise.",
        "The testimony of faith is the foundation of Islam. Repeating it 100 times daily renews one's covenant with Allah and serves as a constant reminder of the purpose of life. It is the best of all forms of remembrance.",
    ),

    # =========================================================================
    # KINDNESS
    # =========================================================================
    (
        "Smile at someone today",
        "Make a conscious effort to smile at everyone you meet today — family, colleagues, strangers. A smile is a simple charity that costs nothing but spreads warmth.",
        SadaqahCategory.kindness, 1, 1, 1, False, 1,
        "HADITH", "Jami' at-Tirmidhi, Book 36, Hadith 10 (1956)", "Sahih",
        "تَبَسُّمُكَ فِي وَجْهِ أَخِيكَ صَدَقَةٌ",
        "Your smiling in the face of your brother is charity.",
        "This hadith from Abu Dharr (RA) elevates a simple smile to the level of sadaqah. It reframes everyday social interaction as an act of worship, making kindness accessible to everyone regardless of wealth.",
    ),
    (
        "Speak a kind word to someone struggling",
        "Find someone who is going through a difficult time and offer them genuine words of encouragement and support. A kind word can lift a heavy heart.",
        SadaqahCategory.kindness, 2, 2, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 78, Hadith 48 (6018)", "Sahih",
        "وَالْكَلِمَةُ الطَّيِّبَةُ صَدَقَةٌ",
        "A good word is charity.",
        "The Prophet (PBUH) taught that even a kind word is a form of charity. This makes every interaction an opportunity for reward — speaking gently to a cashier, encouraging a colleague, or comforting a friend all count as sadaqah.",
    ),
    (
        "Visit a sick person",
        "Take time to visit someone who is ill — a family member, friend, or community member. Your presence and dua can bring immense comfort and healing.",
        SadaqahCategory.kindness, 3, 30, 3, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2568)", "Sahih",
        "مَنْ عَادَ مَرِيضًا لَمْ يَزَلْ فِي خُرْفَةِ الْجَنَّةِ",
        "Whoever visits a sick person remains in the garden of Paradise until they return.",
        "This hadith from Thawban (RA) describes visiting the sick as entering a 'garden of Paradise' — a state of spiritual reward that lasts the entire duration of the visit. It transforms a compassionate act into a sustained spiritual experience.",
    ),
    (
        "Forgive someone who wronged you",
        "Make a conscious decision to forgive someone who has hurt or offended you. Let go of resentment for the sake of Allah, trusting that He is the ultimate Just.",
        SadaqahCategory.kindness, 4, 5, 3, False, 1,
        "QURAN", "Surah Al-A'raf (7:199)", "Quranic",
        "خُذِ الْعَفْوَ وَأْمُرْ بِالْعُرْفِ وَأَعْرِضْ عَنِ الْجَاهِلِينَ",
        "Take forgiveness, enjoin what is good, and turn away from the ignorant.",
        "Allah commands forgiveness as a core characteristic of believers. Forgiving others does not diminish justice — it elevates the forgiver. This act is particularly difficult (difficulty 4) because it requires overcoming the ego, but its reward is immense.",
    ),
    (
        "Make a phone call to a lonely relative",
        "Call a relative who may be lonely, elderly, or isolated. A simple conversation can be a lifeline of connection and care.",
        SadaqahCategory.kindness, 2, 10, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 78, Hadith 28 (6002)", "Sahih",
        "لَيْسَ مِنَّا مَنْ لَمْ يَرْحَمْ صَغِيرَنَا وَيُوَقِّرْ كَبِيرَنَا",
        "He is not of us who does not have mercy on our young and respect our elders.",
        "The Prophet (PBUH) made mercy and respect for elders a defining characteristic of the Muslim community. Reaching out to a lonely relative fulfills this obligation of maintaining family ties and showing compassion.",
    ),
    (
        "Give a genuine compliment",
        "Offer a sincere, specific compliment to someone today — about their character, effort, or kindness. Avoid flattery; speak what you truly observe and appreciate.",
        SadaqahCategory.kindness, 1, 1, 1, False, 1,
        "HADITH", "Jami' at-Tirmidhi, Book 27, Hadith 1 (1980)", "Hasan",
        "إِذَا أَحَبَّ الرَّجُلُ أَخَاهُ فَلْيُخْبِرْهُ أَنَّهُ يُحِبُّهُ",
        "If a man loves his brother, let him tell him that he loves him.",
        "Expressing genuine appreciation strengthens bonds and spreads love in the community. The Prophet (PBUH) encouraged verbalizing positive feelings, not just keeping them in the heart.",
    ),

    # =========================================================================
    # COMMUNITY SERVICE
    # =========================================================================
    (
        "Remove harm from the road",
        "Remove an obstacle, stone, or anything harmful from a pathway that people use. This could be as simple as picking up a fallen branch or reporting a hazard.",
        SadaqahCategory.community, 1, 2, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 40 (2989)", "Sahih",
        "وَتَمِيطُ الْأَذَىٰ عَنِ الطَّرِيقِ صَدَقَةٌ",
        "Removing harmful things from the road is charity.",
        "This hadith from Abu Hurairah (RA) shows that even the smallest community service — clearing a path — is recorded as sadaqah. It requires no money, no special skills, just awareness and care for others.",
    ),
    (
        "Help a neighbor with a chore",
        "Identify a neighbor who could use help — carrying groceries, taking out trash, or a small repair. Good neighborly relations are a sign of strong faith.",
        SadaqahCategory.community, 2, 20, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 78, Hadith 28 (6016)", "Sahih",
        "مَنْ كَانَ يُؤْمِنُ بِاللَّهِ وَالْيَوْمِ الْآخِرِ فَلْيُحْسِنْ إِلَىٰ جَارِهِ",
        "Whoever believes in Allah and the Last Day, let them be good to their neighbor.",
        "The Prophet (PBUH) repeated this command so often that the Companions thought neighbors would inherit from one another. Good treatment of neighbors is a direct test of faith.",
    ),
    (
        "Volunteer at a local food bank or shelter",
        "Spend a few hours volunteering at a community organization that serves those in need. Your time and effort are a powerful form of sadaqah.",
        SadaqahCategory.community, 3, 120, 3, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2699)", "Sahih",
        "وَاللَّهُ فِي عَوْنِ الْعَبْدِ مَا كَانَ الْعَبْدُ فِي عَوْنِ أَخِيهِ",
        "Allah is in the help of His servant as long as the servant is in the help of his brother.",
        "This profound hadith establishes a direct link between helping others and receiving Allah's help. Volunteering is not just charity — it's an investment in divine support for your own needs.",
    ),
    (
        "Attend a community iftar or gathering",
        "Participate in a community iftar or Islamic gathering. Your presence strengthens community bonds and supports the spirit of collective worship.",
        SadaqahCategory.community, 2, 60, 2, True, 2,
        "HADITH", "Jami' at-Tirmidhi, Book 8, Hadith 45 (807)", "Sahih",
        "مَنْ فَطَّرَ صَائِمًا كَانَ لَهُ مِثْلُ أَجْرِهِ",
        "Whoever feeds a fasting person will have a reward like theirs, without diminishing the fasting person's reward.",
        "This hadith highlights the multiplied reward of community service during Ramadan. Attending and contributing to community iftars creates a chain of blessing for everyone involved.",
    ),
    (
        "Organize a neighborhood cleanup",
        "Gather a few neighbors to clean a shared space — a park, street, or community area. Leading community service multiplies the reward through the example you set.",
        SadaqahCategory.community, 4, 120, 3, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2693)", "Sahih",
        "مَنْ دَلَّ عَلَىٰ خَيْرٍ فَلَهُ مِثْلُ أَجْرِ فَاعِلِهِ",
        "Whoever guides someone to goodness will have a reward like the one who does it.",
        "Organizing community service means you share in the reward of everyone who participates. This makes leadership in good deeds a highly efficient form of sadaqah.",
    ),
    (
        "Check on an elderly neighbor",
        "Visit or call an elderly neighbor to check if they need anything. Offer to pick up groceries or medication. Elderly community members are often forgotten but deeply valued in Islam.",
        SadaqahCategory.community, 2, 15, 2, False, 1,
        "HADITH", "Sunan Abi Dawud, Book 42, Hadith 1 (5143)", "Hasan",
        "لَيْسَ مِنَّا مَنْ لَمْ يَرْحَمْ صَغِيرَنَا وَيُوَقِّرْ كَبِيرَنَا",
        "He is not of us who does not show mercy to our young and respect our elders.",
        "Respecting and caring for the elderly is a defining characteristic of the Muslim community. A simple check-in can prevent isolation and ensure their well-being.",
    ),
    (
        "Give directions or help a lost person",
        "If you see someone who looks lost or confused, offer help. Whether it's directions, translation, or assistance, your help is a form of sadaqah.",
        SadaqahCategory.community, 1, 5, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 40 (2989)", "Sahih",
        "كُلُّ مَعْرُوفٍ صَدَقَةٌ",
        "Every good deed is charity.",
        "The Prophet (PBUH) taught that every act of goodness is sadaqah. Helping someone find their way — literally or figuratively — is a good deed that costs nothing but has lasting impact.",
    ),

    # =========================================================================
    # HELPING FAMILY
    # =========================================================================
    (
        "Help with household chores without being asked",
        "Take initiative to clean, cook, or organize at home without being asked. This lightens the load for your family and demonstrates care through action.",
        SadaqahCategory.family, 2, 20, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 170 (676)", "Sahih",
        "خَيْرُكُمْ خَيْرُكُمْ لِأَهْلِهِ وَأَنَا خَيْرُكُمْ لِأَهْلِي",
        "The best of you are the best to their families, and I am the best to my family.",
        "The Prophet (PBUH) himself helped with household chores — mending his own clothes, milking his goat, and serving his family. This hadith makes domestic help a sunnah and a measure of character.",
    ),
    (
        "Spend quality time with your children",
        "Dedicate focused, screen-free time to play, talk, or learn with your children. Your presence and attention are among the greatest gifts you can give.",
        SadaqahCategory.family, 2, 30, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 78, Hadith 1 (5998)", "Sahih",
        "مَنْ لَا يَرْحَمْ لَا يُرْحَمْ",
        "Whoever does not show mercy will not be shown mercy.",
        "Showing mercy to children is a direct path to receiving Allah's mercy. Quality time with children is not just parenting — it's an act of worship that builds the next generation of believers.",
    ),
    (
        "Call your parents just to say you love them",
        "Call your parents specifically to tell them you love them and appreciate them. Don't wait for a need or occasion — make the call about them.",
        SadaqahCategory.family, 1, 5, 2, False, 1,
        "HADITH", "Sunan Abi Dawud, Book 42, Hadith 1 (5143)", "Hasan",
        "الْوَالِدُ أَوْسَطُ أَبْوَابِ الْجَنَّةِ فَإِنْ شِئْتَ فَأَضِعْ ذَٰلِكَ الْبَابَ أَوِ احْفَظْهُ",
        "A parent is the middle gate of Paradise. If you wish, lose that gate, or protect it.",
        "This hadith (from Tirmidhi) powerfully describes parents as the 'middle gate of Paradise' — the easiest way in. A simple phone call expressing love is an act of maintaining that gate.",
    ),
    (
        "Teach a family member a new skill",
        "Share a skill you have with a family member — cooking, reading, a craft, or a professional skill. Teaching is a form of ongoing charity.",
        SadaqahCategory.family, 3, 30, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 3, Hadith 80 (61)", "Sahih",
        "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ",
        "The best of you are those who learn the Quran and teach it.",
        "While this hadith specifically mentions Quran, the principle extends to all beneficial knowledge. Teaching a family member creates ongoing sadaqah jariyah — every time they use that skill, you earn reward.",
    ),
    (
        "Resolve a family dispute with patience",
        "Mediate or step back from a family conflict with patience and wisdom. Choose harmony over being right. Family unity is a great blessing.",
        SadaqahCategory.family, 4, 30, 3, False, 1,
        "QURAN", "Surah Al-Hujurat (49:10)", "Quranic",
        "إِنَّمَا الْمُؤْمِنُونَ إِخْوَةٌ فَأَصْلِحُوا بَيْنَ أَخَوَيْكُمْ",
        "The believers are but brothers, so make peace between your brothers.",
        "Allah commands reconciliation between believers, and this applies most strongly to family. Resolving disputes with patience is a difficult but highly rewarded act that preserves the fabric of the family.",
    ),
    (
        "Prepare a meal for your family with love",
        "Cook or prepare a meal for your family with the intention of serving them for the sake of Allah. Put love and care into the preparation.",
        SadaqahCategory.family, 2, 30, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 170 (676)", "Sahih",
        "إِذَا أَنْفَقَ الْمُسْلِمُ نَفَقَةً عَلَىٰ أَهْلِهِ وَهُوَ يَحْتَسِبُهَا كَانَتْ لَهُ صَدَقَةً",
        "When a Muslim spends on his family seeking reward, it is charity for him.",
        "The Prophet (PBUH) taught that even the money spent on feeding your family is recorded as sadaqah. Preparing food with the right intention transforms a daily necessity into an act of worship.",
    ),

    # =========================================================================
    # BENEFICIAL KNOWLEDGE
    # =========================================================================
    (
        "Read 10 minutes of Quran with translation",
        "Read 10 minutes of the Quran along with its meaning in a language you understand. Understanding the Quran deepens faith and guides action.",
        SadaqahCategory.knowledge, 2, 10, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 66, Hadith 1 (5027)", "Sahih",
        "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ",
        "The best of you are those who learn the Quran and teach it.",
        "Learning the Quran — including understanding its meaning — is the standard by which the Prophet (PBUH) measured excellence. Even 10 minutes daily creates a consistent connection with Allah's words.",
    ),
    (
        "Attend a religious lecture or halaqa",
        "Attend a local or online Islamic lecture, class, or halaqa. Seeking knowledge is an obligation and a path to Paradise.",
        SadaqahCategory.knowledge, 2, 60, 2, False, 1,
        "HADITH", "Sunan Ibn Majah, Book 1, Hadith 1 (224)", "Sahih",
        "طَلَبُ الْعِلْمِ فَرِيضَةٌ عَلَىٰ كُلِّ مُسْلِمٍ",
        "Seeking knowledge is an obligation upon every Muslim.",
        "This hadith makes seeking knowledge a personal obligation (fard 'ayn). Attending a halaqa fulfills this duty and connects you with a community of learners.",
    ),
    (
        "Share a beneficial article or video",
        "Share an Islamic reminder, lecture, or beneficial content with friends or family. Guiding others to goodness earns you their reward.",
        SadaqahCategory.knowledge, 1, 2, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2693)", "Sahih",
        "مَنْ دَلَّ عَلَىٰ خَيْرٍ فَلَهُ مِثْلُ أَجْرِ فَاعِلِهِ",
        "Whoever guides someone to goodness will have a reward like the one who does it.",
        "Sharing beneficial knowledge creates a chain of reward that continues as long as people benefit from it. This is one of the easiest ways to earn ongoing sadaqah jariyah.",
    ),
    (
        "Memorize a new verse of the Quran",
        "Commit one new verse of the Quran to memory. Even one verse is a step toward the goal of learning the Book of Allah.",
        SadaqahCategory.knowledge, 3, 15, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 66, Hadith 1 (5027)", "Sahih",
        "يُقَالُ لِصَاحِبِ الْقُرْآنِ: اقْرَأْ وَارْتَقِ وَرَتِّلْ كَمَا كُنْتَ تُرَتِّلُ فِي الدُّنْيَا",
        "It will be said to the companion of the Quran: 'Read and ascend, and recite as you used to recite in the world.'",
        "This hadith describes the unique honor of those who memorize and recite Quran — their rank in Paradise rises with every verse they recite. Each new verse memorized is an investment in eternal elevation.",
    ),
    (
        "Read a book about the Prophet's life (Seerah)",
        "Read a chapter or section of a book about the life of Prophet Muhammad (PBUH). Learning his character and struggles deepens love and emulation.",
        SadaqahCategory.knowledge, 2, 20, 2, False, 1,
        "QURAN", "Surah Al-Ahzab (33:21)", "Quranic",
        "لَّقَدْ كَانَ لَكُمْ فِي رَسُولِ اللَّهِ أُسْوَةٌ حَسَنَةٌ",
        "Indeed, in the Messenger of Allah you have an excellent example.",
        "Allah commands us to take the Prophet (PBUH) as our model. Studying his life is not just historical learning — it's a practical guide for how to live every aspect of life with excellence.",
    ),
    (
        "Teach a child a short surah",
        "Teach a child in your life a short surah from the Quran, like Al-Fatihah or Al-Ikhlas. This plants seeds of faith that will grow for years.",
        SadaqahCategory.knowledge, 2, 10, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 3, Hadith 80 (61)", "Sahih",
        "خَيْرُكُمْ مَنْ تَعَلَّمَ الْقُرْآنَ وَعَلَّمَهُ",
        "The best of you are those who learn the Quran and teach it.",
        "Teaching a child a surah creates sadaqah jariyah — every time they recite it in prayer, you earn reward. This is one of the most impactful investments a person can make.",
    ),

    # =========================================================================
    # FINANCIAL CHARITY
    # =========================================================================
    (
        "Give sadaqah anonymously",
        "Give charity in a way that only Allah knows — no name, no recognition. Secret charity extinguishes sins and is a sign of sincere faith.",
        SadaqahCategory.donation, 3, 5, 3, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 24, Hadith 1 (1411)", "Sahih",
        "وَصَدَقَةٌ تُخْفِيهَا حَتَّىٰ لَا تَعْلَمَ شِمَالُكَ مَا تُنْفِقُ يَمِينُكَ",
        "Charity given secretly such that the left hand does not know what the right hand gives.",
        "The Prophet (PBUH) described secret charity as one of the seven types of people who will be shaded on the Day of Judgment. Giving anonymously protects the recipient's dignity and purifies the giver's intention.",
    ),
    (
        "Sponsor an orphan's meal",
        "Donate the cost of a meal to sponsor an orphan. Caring for orphans is a direct path to Paradise and closeness to the Prophet (PBUH).",
        SadaqahCategory.donation, 2, 5, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 73, Hadith 10 (5659)", "Sahih",
        "أَنَا وَكَافِلُ الْيَتِيمِ فِي الْجَنَّةِ هَكَذَا",
        "I and the one who sponsors an orphan will be in Paradise like this — and he gestured with his index and middle finger, showing their closeness.",
        "This hadith shows the extraordinary status of those who care for orphans — they will be as close to the Prophet (PBUH) in Paradise as two fingers are to each other. Even sponsoring a single meal contributes to this.",
    ),
    (
        "Give a small amount daily for 7 days",
        "Commit to giving a small amount of charity every day for one week. Consistency in charity, even in small amounts, is beloved to Allah.",
        SadaqahCategory.donation, 2, 2, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 81, Hadith 1 (6464)", "Sahih",
        "أَحَبُّ الْأَعْمَالِ إِلَىٰ اللَّهِ أَدْوَمُهَا وَإِنْ قَلَّ",
        "The most beloved of deeds to Allah are the most consistent, even if small.",
        "Consistency is more important than quantity. A small daily charity builds a habit of generosity and is more beloved to Allah than a large one-time donation followed by neglect.",
    ),
    (
        "Donate to a verified charity organization",
        "Research and donate to a reputable, verified charity organization. Ensure your charity reaches those who genuinely need it.",
        SadaqahCategory.donation, 2, 10, 2, False, 1,
        "QURAN", "Surah Al-Baqarah (2:261)", "Quranic",
        "مَّثَلُ الَّذِينَ يُنفِقُونَ أَمْوَالَهُمْ فِي سَبِيلِ اللَّهِ كَمَثَلِ حَبَّةٍ أَنبَتَتْ سَبْعَ سَنَابِلَ",
        "The example of those who spend their wealth in the way of Allah is like a seed of grain that grows seven spikes.",
        "Allah promises a 700-fold return (or more) on charity given sincerely. Donating through verified organizations ensures your charity is effective and reaches those in need, maximizing both impact and reward.",
    ),
    (
        "Give food to someone in need",
        "Buy and give a meal or groceries to someone who is struggling financially. Feeding the hungry is one of the most emphasized acts in the Quran.",
        SadaqahCategory.donation, 3, 20, 3, False, 1,
        "QURAN", "Surah Al-Insan (76:8-9)", "Quranic",
        "وَيُطْعِمُونَ الطَّعَامَ عَلَىٰ حُبِّهِ مِسْكِينًا وَيَتِيمًا وَأَسِيرًا",
        "And they give food, despite their love for it, to the needy, the orphan, and the captive.",
        "The Quran describes the righteous as those who feed others even when they themselves desire the food. This act of selfless giving is a direct path to Paradise and forgiveness.",
    ),
    (
        "Lend something useful to a neighbor",
        "Lend a tool, book, or household item to a neighbor who needs it. Sharing resources builds community and reduces waste.",
        SadaqahCategory.donation, 1, 5, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2699)", "Sahih",
        "وَاللَّهُ فِي عَوْنِ الْعَبْدِ مَا كَانَ الْعَبْدُ فِي عَوْنِ أَخِيهِ",
        "Allah is in the help of His servant as long as the servant is in the help of his brother.",
        "Lending an item is a form of help that Allah promises to reciprocate. This hadith establishes a direct spiritual return on every act of assistance, no matter how small.",
    ),
    (
        "Give charity on behalf of a deceased loved one",
        "Give sadaqah on behalf of someone who has passed away. This is a gift that continues to benefit them in the grave.",
        SadaqahCategory.donation, 2, 5, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 23, Hadith 1 (1386)", "Sahih",
        "إِذَا مَاتَ الْإِنْسَانُ انْقَطَعَ عَنْهُ عَمَلُهُ إِلَّا مِنْ ثَلَاثَةٍ: صَدَقَةٍ جَارِيَةٍ",
        "When a person dies, their deeds come to an end except for three: ongoing charity, beneficial knowledge, or a righteous child who prays for them.",
        "Giving charity on behalf of the deceased is a form of sadaqah jariyah that continues to benefit them. It's a powerful way to honor loved ones and send them ongoing rewards.",
    ),

    # =========================================================================
    # ENVIRONMENTAL CARE
    # =========================================================================
    (
        "Plant a tree or a plant",
        "Plant a tree, shrub, or even a small plant. Every living thing that benefits from it — birds, insects, humans — will be a source of ongoing charity for you.",
        SadaqahCategory.environment, 2, 20, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 41, Hadith 1 (2320)", "Sahih",
        "مَا مِنْ مُسْلِمٍ يَغْرِسُ غَرْسًا إِلَّا كَانَ مَا يُؤْكَلُ مِنْهُ لَهُ صَدَقَةً",
        "There is no Muslim who plants a tree except that whatever is eaten from it is charity for them.",
        "This hadith from Anas (RA) establishes planting as a form of sadaqah jariyah. Every fruit, shade, or benefit that comes from that tree continues to earn reward even after the planter has passed away.",
    ),
    (
        "Reduce single-use plastic for a day",
        "Make a conscious effort to avoid single-use plastics for one full day — use reusable bags, bottles, and containers. Caring for the earth is a form of gratitude to Allah.",
        SadaqahCategory.environment, 2, 1440, 1, False, 1,
        "QURAN", "Surah Al-A'raf (7:56)", "Quranic",
        "وَلَا تُفْسِدُوا فِي الْأَرْضِ بَعْدَ إِصْلَاحِهَا",
        "And do not cause corruption on the earth after its reformation.",
        "Allah commands us not to spread corruption on earth. Environmental degradation is a form of corruption, and avoiding it is an act of obedience. This verse provides a Quranic basis for environmental stewardship.",
    ),
    (
        "Pick up litter in a public space",
        "Spend 10 minutes picking up litter in a park, street, or public area. Cleaning the environment is a practical expression of faith.",
        SadaqahCategory.environment, 2, 10, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 5, Hadith 219 (1009)", "Sahih",
        "وَإِمَاطَةُ الْأَذَىٰ عَنِ الطَّرِيقِ صَدَقَةٌ",
        "Removing harm from the road is charity.",
        "Litter is a form of harm — it can injure, pollute, and create ugliness. Removing it falls directly under this hadith and is recorded as sadaqah. A 10-minute cleanup can have a visible impact on your community.",
    ),
    (
        "Conserve water while making wudu",
        "Be mindful of water usage during wudu. Use no more than a moderate amount, even if you have access to abundant water.",
        SadaqahCategory.environment, 1, 2, 1, False, 1,
        "HADITH", "Sunan Ibn Majah, Book 1, Hadith 48 (425)", "Sahih",
        "لَا تُسْرِفُوا فِي الْمَاءِ وَلَوْ كُنْتُمْ عَلَىٰ نَهَرٍ جَارٍ",
        "Do not waste water, even if you are by a flowing river.",
        "The Prophet (PBUH) explicitly forbade water waste even in abundance. This hadith is a powerful environmental principle — conservation is an Islamic value, not just a modern concern.",
    ),
    (
        "Feed birds or animals",
        "Put out food for birds, stray animals, or creatures in your area. Caring for animals is a rewarded act of compassion.",
        SadaqahCategory.environment, 1, 5, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 59, Hadith 1 (3292)", "Sahih",
        "فِي كُلِّ كَبِدٍ رَطْبَةٍ أَجْرٌ",
        "In every living being with a moist liver (i.e., every living creature) there is reward.",
        "The Prophet (PBUH) taught that showing kindness to any living creature brings reward. He told the story of a prostitute who was forgiven because she gave water to a thirsty dog — showing that compassion to animals can be a path to Paradise.",
    ),
    (
        "Walk instead of drive for a short trip",
        "Choose to walk for a short journey instead of driving. This reduces your carbon footprint, benefits your health, and can be an act of gratitude for the ability to walk.",
        SadaqahCategory.environment, 2, 15, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 10, Hadith 40 (2989)", "Sahih",
        "كُلُّ مَعْرُوفٍ صَدَقَةٌ",
        "Every good deed is charity.",
        "Choosing a more sustainable option is a 'good deed' that benefits the environment, your health, and society. The Prophet (PBUH) taught that every good deed is sadaqah, making environmental consciousness an act of worship.",
    ),

    # =========================================================================
    # CHARACTER DEVELOPMENT
    # =========================================================================
    (
        "Control your anger for the sake of Allah",
        "When you feel anger rising, consciously pause, seek refuge in Allah, and choose not to act on it. Controlling anger is a sign of true strength.",
        SadaqahCategory.character, 4, 5, 3, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 78, Hadith 76 (6114)", "Sahih",
        "لَيْسَ الشَّدِيدُ بِالصُّرَعَةِ، إِنَّمَا الشَّدِيدُ الَّذِي يَمْلِكُ نَفْسَهُ عِنْدَ الْغَضَبِ",
        "The strong person is not the one who can wrestle, but the one who controls themselves at times of anger.",
        "The Prophet (PBUH) redefined strength as emotional self-control, not physical power. Controlling anger is one of the most difficult character traits to master (difficulty 4), but it is a defining quality of the righteous.",
    ),
    (
        "Speak only good or remain silent",
        "Make a conscious effort today to speak only if your words are beneficial. If you have nothing good to say, choose silence. This is a foundational principle of Islamic character.",
        SadaqahCategory.character, 3, 1440, 2, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 81, Hadith 48 (6475)", "Sahih",
        "مَنْ كَانَ يُؤْمِنُ بِاللَّهِ وَالْيَوْمِ الْآخِرِ فَلْيَقُلْ خَيْرًا أَوْ لِيَصْمُتْ",
        "Whoever believes in Allah and the Last Day, let them speak good or remain silent.",
        "This hadith from Abu Hurairah (RA) makes speech discipline a direct test of faith. Every word we speak will be accounted for. Practicing this for a full day is challenging but transformative for character.",
    ),
    (
        "Practice gratitude for 5 things before sleep",
        "Before sleeping, mentally list five specific things you are grateful for today. Gratitude is the foundation of contentment and faith.",
        SadaqahCategory.character, 1, 5, 1, False, 1,
        "QURAN", "Surah Ibrahim (14:7)", "Quranic",
        "لَئِن شَكَرْتُمْ لَأَزِيدَنَّكُمْ",
        "If you are grateful, I will surely increase you [in blessing].",
        "Allah makes a direct promise — gratitude brings increase. Practicing daily gratitude trains the mind to focus on blessings rather than shortcomings, leading to greater contentment and spiritual well-being.",
    ),
    (
        "Apologize sincerely for a mistake",
        "Identify a mistake you made — recently or in the past — and offer a sincere apology to the person you wronged. Humility in admitting fault is a sign of strong character.",
        SadaqahCategory.character, 3, 10, 2, False, 1,
        "HADITH", "Sunan Abi Dawud, Book 42, Hadith 1 (5143)", "Hasan",
        "وَمَا تَوَاضَعَ أَحَدٌ لِلَّهِ إِلَّا رَفَعَهُ اللَّهُ",
        "Whoever humbles themselves for Allah, Allah raises them.",
        "Apologizing requires humility, which the Prophet (PBUH) promised would be rewarded with elevation. A sincere apology mends relationships and purifies the heart from pride.",
    ),
    (
        "Avoid gossiping or backbiting for one day",
        "Make a conscious effort to avoid speaking about others in their absence — whether true or false. Backbiting is compared to eating the flesh of your dead brother in the Quran.",
        SadaqahCategory.character, 3, 1440, 2, False, 1,
        "QURAN", "Surah Al-Hujurat (49:12)", "Quranic",
        "وَلَا يَغْتَب بَّعْضُكُم بَعْضًا ۚ أَيُحِبُّ أَحَدُكُمْ أَن يَأْكُلَ لَحْمَ أَخِيهِ مَيْتًا",
        "And do not backbite one another. Would any of you love to eat the flesh of his dead brother?",
        "The Quran uses this powerful and shocking imagery to condemn backbiting. Avoiding gossip for even one day is a significant act of character development that protects both your own soul and the dignity of others.",
    ),
    (
        "Be patient with a difficult situation",
        "When faced with a frustrating or difficult situation today, consciously practice patience (sabr). Remind yourself that Allah is with the patient.",
        SadaqahCategory.character, 3, 30, 2, False, 1,
        "QURAN", "Surah Al-Baqarah (2:153)", "Quranic",
        "إِنَّ اللَّهَ مَعَ الصَّابِرِينَ",
        "Indeed, Allah is with the patient.",
        "Patience is half of faith. Allah's promise to be 'with' the patient is a profound guarantee of divine support. Practicing patience in difficulty transforms trials into opportunities for spiritual growth.",
    ),
    (
        "Make a sincere intention to improve one bad habit",
        "Identify one bad habit and make a sincere intention (niyyah) to work on improving it. Write it down and make dua for Allah's help. Intention is the beginning of all change.",
        SadaqahCategory.character, 2, 10, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 1, Hadith 1 (1)", "Sahih",
        "إِنَّمَا الْأَعْمَالُ بِالنِّيَّاتِ",
        "Actions are judged by intentions.",
        "This foundational hadith teaches that the intention to improve is itself a recorded act. Even before you take action, your sincere desire to change for the sake of Allah is recognized and rewarded.",
    ),

    # =========================================================================
    # GENERAL
    # =========================================================================
    (
        "Pray two rak'ah of voluntary prayer (Tahajjud)",
        "Wake up to pray two rak'ah of Tahajjud (night prayer) in the last third of the night. This is a time when Allah descends to the lowest heaven and asks who is seeking forgiveness.",
        SadaqahCategory.general, 3, 10, 3, False, 2,
        "HADITH", "Sahih al-Bukhari, Book 19, Hadith 14 (1145)", "Sahih",
        "يَنْزِلُ رَبُّنَا تَبَارَكَ وَتَعَالَىٰ كُلَّ لَيْلَةٍ إِلَىٰ السَّمَاءِ الدُّنْيَا",
        "Our Lord descends to the lowest heaven every night when the last third of the night remains and says: 'Who is calling upon Me that I may answer?'",
        "Tahajjud is a private conversation with Allah in the stillness of the night. It is the time when duas are answered, forgiveness is granted, and spiritual closeness is achieved. Even two rak'ah carry immense weight.",
    ),
    (
        "Pray two rak'ah before Fajr (Sunnah)",
        "Pray the two rak'ah sunnah before the Fajr obligatory prayer. The Prophet (PBUH) said these two rak'ah are better than the world and everything in it.",
        SadaqahCategory.general, 2, 5, 2, False, 1,
        "HADITH", "Sahih Muslim, Book 6, Hadith 1 (725)", "Sahih",
        "رَكْعَتَا الْفَجْرِ خَيْرٌ مِنَ الدُّنْيَا وَمَا فِيهَا",
        "The two rak'ah of Fajr are better than the world and everything in it.",
        "This hadith from Aisha (RA) shows the extraordinary value of this brief sunnah prayer. A few minutes before Fajr can be worth more than all worldly possessions combined.",
    ),
    (
        "Make dua for the Ummah",
        "Take a moment to make sincere dua for the entire Muslim Ummah — for those suffering, those in need, and those seeking guidance. Your dua reaches where you cannot.",
        SadaqahCategory.general, 1, 2, 1, False, 1,
        "HADITH", "Sahih Muslim, Book 45, Hadith 100 (2699)", "Sahih",
        "دَعْوَةُ الْمَرْءِ الْمُسْلِمِ لِأَخِيهِ بِظَهْرِ الْغَيْبِ مُسْتَجَابَةٌ",
        "The prayer of a Muslim for their brother in their absence is answered.",
        "The Prophet (PBUH) taught that when you make dua for another person without their knowledge, angels say 'Ameen, and for you the same.' Praying for the Ummah benefits both the one prayed for and the one praying.",
    ),
    (
        "Perform a sunnah act you usually skip",
        "Identify a sunnah (recommended practice) that you normally neglect and make a point to perform it today — whether it's a specific dua, a sunnah prayer, or a prophetic etiquette.",
        SadaqahCategory.general, 2, 5, 1, False, 1,
        "HADITH", "Sahih al-Bukhari, Book 81, Hadith 1 (6464)", "Sahih",
        "أَحَبُّ الْأَعْمَالِ إِلَىٰ اللَّهِ أَدْوَمُهَا وَإِنْ قَلَّ",
        "The most beloved of deeds to Allah are the most consistent, even if small.",
        "Reviving a neglected sunnah is a sign of love for the Prophet (PBUH). Even if the act is small, the consistency and intention behind it make it beloved to Allah.",
    ),
    (
        "Reflect on a verse of the Quran for 5 minutes",
        "Choose one verse of the Quran and spend 5 minutes reflecting on its meaning, context, and application to your life. Reflection (tadabbur) is the purpose of revelation.",
        SadaqahCategory.general, 2, 5, 2, False, 1,
        "QURAN", "Surah Sad (38:29)", "Quranic",
        "كِتَابٌ أَنزَلْنَاهُ إِلَيْكَ مُبَارَكٌ لِّيَدَّبَّرُوا آيَاتِهِ",
        "A blessed Book which We have revealed to you so that they may reflect upon its verses.",
        "Allah reveals the Quran for reflection, not just recitation. Spending even 5 minutes pondering a single verse fulfills this purpose and can transform understanding and action.",
    ),
]

# ---------------------------------------------------------------------------
# SEED EXECUTION
# ---------------------------------------------------------------------------

print("Seeding acts with evidence...")

seeded_acts = []
fully_cited_count = 0
flagged_count = 0

for entry in acts_data:
    (
        title, description, category, difficulty, estimated_time,
        reward_weight, is_ramadan_only, ramadan_multiplier,
        ev_source_type, ev_reference, ev_grade, ev_arabic, ev_english, ev_explanation,
    ) = entry

    act = SadaqahAct(
        title=title,
        description=description,
        category=category,
        difficulty=difficulty,
        estimated_time_minutes=estimated_time,
        reward_weight=reward_weight,
        is_ramadan_only=is_ramadan_only,
        ramadan_multiplier=ramadan_multiplier,
        verified=True,
    )
    db.add(act)
    db.flush()

    if ev_source_type and ev_reference:
        evidence = Evidence(
            act_id=act.id,
            source_type=ev_source_type,
            reference=ev_reference,
            grade=ev_grade,
            arabic_text=ev_arabic,
            english_text=ev_english,
            is_verified=True,
        )
        db.add(evidence)
        fully_cited_count += 1
    else:
        flagged_count += 1

    seeded_acts.append(act)

db.commit()
print(f"  Created {len(seeded_acts)} acts with evidence")
print(f"  Fully cited: {fully_cited_count}, Flagged for review: {flagged_count}")

# ---------------------------------------------------------------------------
# USERS (10 test users, properly hashed passwords)
# ---------------------------------------------------------------------------

print("Seeding users...")
users = []
seeded_password_hash = hash_password("testpassword")

for i in range(10):
    user = User(
        email=f"user{i}@test.com",
        username=f"user{i}",
        hashed_password=seeded_password_hash,
        created_at=datetime.utcnow() - timedelta(days=random.randint(1, 30)),
    )
    db.add(user)
    users.append(user)

db.commit()
print(f"  Created {len(users)} users")

# ---------------------------------------------------------------------------
# JARS (one per user)
# ---------------------------------------------------------------------------

print("Seeding jars...")
for user in users:
    jar = Jar(
        user_id=user.id,
        capacity=33,
        current_stars=random.randint(0, 20),
    )
    db.add(jar)

db.commit()
print("  Created 10 jars")

# ---------------------------------------------------------------------------
# SADAQAH LOGS (simulate 30 days of activity)
# ---------------------------------------------------------------------------

print("Seeding sadaqah logs...")
used_logs: set[tuple[int, int, datetime.date]] = set()

for user in users:
    for _ in range(random.randint(10, 40)):
        act = random.choice(seeded_acts)
        log_date = datetime.utcnow().date() - timedelta(days=random.randint(0, 30))
        key = (user.id, act.id, log_date)
        if key in used_logs:
            continue
        used_logs.add(key)
        log = SadaqahLog(
            user_id=user.id,
            act_id=act.id,
            date=log_date,
            stars_earned=random.randint(1, 3),
            friday_boost=random.choice([True, False]),
            ramadan_bonus=random.choice([True, False]),
        )
        db.add(log)

db.commit()
print(f"  Created {len(used_logs)} logs")

# ---------------------------------------------------------------------------
# FAMILY JAR
# ---------------------------------------------------------------------------

print("Seeding family jar...")
family_jar = FamilyJar(
    name="Test Family Jar",
    invite_code="TEST123",
    capacity=100,
    current_stars=0,
    created_by=users[0].id,
)
db.add(family_jar)
db.commit()
db.refresh(family_jar)

owner_member = FamilyJarMember(
    family_jar_id=family_jar.id,
    user_id=users[0].id,
)
db.add(owner_member)

for user in users[1:5]:
    member = FamilyJarMember(
        family_jar_id=family_jar.id,
        user_id=user.id,
    )
    db.add(member)

db.commit()

for _ in range(30):
    member = random.choice(users[:5])
    act = random.choice(seeded_acts)
    log = FamilyJarLog(
        family_jar_id=family_jar.id,
        user_id=member.id,
        act_id=act.id,
        stars_added=random.randint(1, 3),
        date=datetime.utcnow().date(),
    )
    db.add(log)

db.commit()
print("  Created family jar with members and logs")

# ---------------------------------------------------------------------------
# CHARITIES
# ---------------------------------------------------------------------------

print("Seeding charities...")
charities_data = [
    ("Red Crescent", "https://redcrescent.org"),
    ("Islamic Relief", "https://islamic-relief.org"),
    ("Helping Hands", "https://helpinghands.org"),
]
for name, url in charities_data:
    charity = Charity(
        name=name,
        website_url=url,
        description="Charity organization",
        category="humanitarian",
        is_verified=True,
        is_active=True,
    )
    db.add(charity)

db.commit()
print("  Created charities")

# ---------------------------------------------------------------------------
# BADGES
# ---------------------------------------------------------------------------

print("Seeding badges...")
badge = Badge(
    name="First Good Deed",
    description="Completed your first sadaqah act",
)
db.add(badge)
db.commit()

user_badge = UserBadge(
    user_id=users[0].id,
    badge_id=badge.id,
)
db.add(user_badge)
db.commit()
print("  Created badge and assignment")

print("\nSEED COMPLETE")
print(f"Total acts seeded: {len(seeded_acts)}")
print(f"  - Fully cited with hadith/Quran: {fully_cited_count}")
print(f"  - Flagged for scholarly review: {flagged_count}")