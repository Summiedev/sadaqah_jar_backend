"""
Seed well-established morning adhkar (remembrances of Allah).

All entries here are from authentic, well-known sources (Sahih al-Bukhari,
Sahih Muslim, authentic hadith collections). The Arabic text and
translations are standard and widely published.

NOTE: I am not a hadith scholar. The specific hadith reference numbers
may vary between editions. These should be verified against a reliable
scholarly source before production use.
"""

from app.db.session import SessionLocal
from app.models.adhkar import Adhkar, TimeOfDay

db = SessionLocal()

entries = [
    # -----------------------------------------------------------------------
    # AYAT AL-KURSI — The greatest verse in the Quran
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ الْحَيُّ الْقَيُّومُ ۚ لَا تَأْخُذُهُ سِنَةٌ وَلَا نَوْمٌ ۚ لَّهُ مَا فِي السَّمَاوَاتِ وَمَا فِي الْأَرْضِ ۚ مَن ذَا الَّذِي يَشْفَعُ عِندَهُ إِلَّا بِإِذْنِهِ ۚ يَعْلَمُ مَا بَيْنَ أَيْدِيهِمْ وَمَا خَلْفَهُمْ ۚ وَلَا يُحِيطُونَ بِشَيْءٍ مِّنْ عِلْمِهِ إِلَّا بِمَا شَاءَ ۚ وَسِعَ كُرْسِيُّهُ السَّمَاوَاتِ وَالْأَرْضَ ۚ وَلَا يَئُودُهُ حِفْظُهُمَا ۚ وَهُوَ الْعَلِيُّ الْعَظِيمُ",
        text_translation="Allah — there is no god except Him, the Ever-Living, the Sustainer of existence. Neither drowsiness nor sleep overtakes Him. To Him belongs whatever is in the heavens and whatever is on the earth...",
        time_of_day=TimeOfDay.morning,
        source="Quran 2:255 — Sahih al-Bukhari 6405 (virtue of reciting after prayers)",
        repeat_count=1,
    ),
    # -----------------------------------------------------------------------
    # SURAH AL-IKHLAS, AL-FALAQ, AN-NAS (the three Quls / al-Mu'awwidhat)
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="قُلْ هُوَ اللَّهُ أَحَدٌ * اللَّهُ الصَّمَدُ * لَمْ يَلِدْ وَلَمْ يُولَدْ * وَلَمْ يَكُن لَّهُ كُفُوًا أَحَدٌ",
        text_translation="Say: He is Allah, the One. Allah, the Eternal Refuge. He neither begets nor is born, nor is there to Him any equivalent.",
        time_of_day=TimeOfDay.morning,
        source="Quran 112 — recited 3x morning and evening (Sunan Abi Dawud 5082)",
        repeat_count=3,
    ),
    Adhkar(
        text_arabic="قُلْ أَعُوذُ بِرَبِّ الْفَلَقِ * مِن شَرِّ مَا خَلَقَ * وَمِن شَرِّ غَاسِقٍ إِذَا وَقَبَ * وَمِن شَرِّ النَّفَّاثَاتِ فِي الْعُقَدِ * وَمِن شَرِّ حَاسِدٍ إِذَا حَسَدَ",
        text_translation="Say: I seek refuge in the Lord of the daybreak, from the evil of what He has created, and from the evil of darkness when it settles...",
        time_of_day=TimeOfDay.morning,
        source="Quran 113 — recited 3x morning and evening (Sunan Abi Dawud 5082)",
        repeat_count=3,
    ),
    Adhkar(
        text_arabic="قُلْ أَعُوذُ بِرَبِّ النَّاسِ * مَلِكِ النَّاسِ * إِلَٰهِ النَّاسِ * مِن شَرِّ الْوَسْوَاسِ الْخَنَّاسِ * الَّذِي يُوَسْوِسُ فِي صُدُورِ النَّاسِ * مِنَ الْجِنَّةِ وَالنَّاسِ",
        text_translation="Say: I seek refuge in the Lord of mankind, the King of mankind, the God of mankind, from the evil of the whisperer who withdraws...",
        time_of_day=TimeOfDay.morning,
        source="Quran 114 — recited 3x morning and evening (Sunan Abi Dawud 5082)",
        repeat_count=3,
    ),
    # -----------------------------------------------------------------------
    # SUBHANALLAH WA BIHAMDIHI 100x
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="سُبْحَانَ اللَّهِ وَبِحَمْدِهِ",
        text_translation="Glory and praise be to Allah.",
        time_of_day=TimeOfDay.morning,
        source="Sahih al-Bukhari 6405 — sins forgiven even if like the foam of the sea",
        repeat_count=100,
    ),
    # -----------------------------------------------------------------------
    # LA ILAHA ILLALLAH, MUHAMMADUR RASULULLAH
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="لَا إِلَٰهَ إِلَّا اللَّهُ وَحْدَهُ لَا شَرِيكَ لَهُ، لَهُ الْمُلْكُ وَلَهُ الْحَمْدُ، وَهُوَ عَلَىٰ كُلِّ شَيْءٍ قَدِيرٌ",
        text_translation="There is no god but Allah alone, with no partner. His is the sovereignty and His is the praise, and He is over all things competent.",
        time_of_day=TimeOfDay.morning,
        source="Sahih al-Bukhari 3293 — whoever says it 10x in the morning gets 10 rewards, 10 sins erased, 10 degrees raised",
        repeat_count=10,
    ),
    # -----------------------------------------------------------------------
    # BISMILLAHI ALLADHI LA YADURRU
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="بِسْمِ اللَّهِ الَّذِي لَا يَضُرُّ مَعَ اسْمِهِ شَيْءٌ فِي الْأَرْضِ وَلَا فِي السَّمَاءِ وَهُوَ السَّمِيعُ الْعَلِيمُ",
        text_translation="In the name of Allah, with whose name nothing can harm on earth or in heaven, and He is the All-Hearing, the All-Knowing.",
        time_of_day=TimeOfDay.morning,
        source="Sunan Abi Dawud 5088 — recited 3x morning and evening, nothing harms you",
        repeat_count=3,
    ),
    # -----------------------------------------------------------------------
    # RADITU BILLAHI RABBA
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="رَضِيتُ بِاللَّهِ رَبًّا، وَبِالْإِسْلَامِ دِينًا، وَبِمُحَمَّدٍ نَبِيًّا",
        text_translation="I am pleased with Allah as my Lord, with Islam as my religion, and with Muhammad as my Prophet.",
        time_of_day=TimeOfDay.morning,
        source="Sunan Abi Dawud 5072 — whoever says it 3x in the morning, it is a guarantee for them on the Day of Judgment",
        repeat_count=3,
    ),
    # -----------------------------------------------------------------------
    # SUBHANALLAH 33x, ALHAMDULILLAH 33x, ALLAHU AKBAR 34x
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="سُبْحَانَ اللَّهِ (٣٣) \nالْحَمْدُ لِلَّهِ (٣٣) \nاللَّهُ أَكْبَرُ (٣٤)",
        text_translation="Glory be to Allah (33 times). Praise be to Allah (33 times). Allah is the Greatest (34 times).",
        time_of_day=TimeOfDay.morning,
        source="Sahih al-Bukhari 843 — the tasbih after every prayer, also recommended morning and evening",
        repeat_count=100,
    ),
    # -----------------------------------------------------------------------
    # ASTAGHFIRULLAH 100x
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="أَسْتَغْفِرُ اللَّهَ وَأَتُوبُ إِلَيْهِ",
        text_translation="I seek forgiveness from Allah and repent to Him.",
        time_of_day=TimeOfDay.morning,
        source="Sahih Muslim 2702 — the Prophet (PBUH) said it 100x daily",
        repeat_count=100,
    ),
    # -----------------------------------------------------------------------
    # ALLAHUMMA BIKA ASBAHNA
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="اللَّهُمَّ بِكَ أَصْبَحْنَا، وَبِكَ أَمْسَيْنَا، وَبِكَ نَحْيَا، وَبِكَ نَمُوتُ، وَإِلَيْكَ النُّشُورُ",
        text_translation="O Allah, by You we enter the morning, by You we enter the evening, by You we live, by You we die, and to You is the resurrection.",
        time_of_day=TimeOfDay.morning,
        source="Sunan Abi Dawud 5068 — morning supplication of the Prophet (PBUH)",
        repeat_count=1,
    ),
    # -----------------------------------------------------------------------
    # ALLAHUMMA INNI AS'ALUKA AL-AFIYAH
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="اللَّهُمَّ إِنِّي أَسْأَلُكَ الْعَافِيَةَ فِي الدُّنْيَا وَالْآخِرَةِ",
        text_translation="O Allah, I ask You for well-being in this world and the Hereafter.",
        time_of_day=TimeOfDay.morning,
        source="Sunan Ibn Majah 3871 — the Prophet (PBUH) never left this supplication morning or evening",
        repeat_count=3,
    ),
    # -----------------------------------------------------------------------
    # HASBIYALLAHU LA ILAHA ILLA HUWA
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="حَسْبِيَ اللَّهُ لَا إِلَٰهَ إِلَّا هُوَ عَلَيْهِ تَوَكَّلْتُ وَهُوَ رَبُّ الْعَرْشِ الْعَظِيمِ",
        text_translation="Sufficient for me is Allah; there is no god except Him. In Him I have placed my trust, and He is the Lord of the Mighty Throne.",
        time_of_day=TimeOfDay.morning,
        source="Quran 9:129 — recited 7x morning and evening (Sunan Abi Dawud 5081)",
        repeat_count=7,
    ),
    # -----------------------------------------------------------------------
    # ALLAHUMMA SALLI ALA MUHAMMAD
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="اللَّهُمَّ صَلِّ عَلَىٰ مُحَمَّدٍ وَعَلَىٰ آلِ مُحَمَّدٍ، كَمَا صَلَّيْتَ عَلَىٰ إِبْرَاهِيمَ وَعَلَىٰ آلِ إِبْرَاهِيمَ، إِنَّكَ حَمِيدٌ مَّجِيدٌ",
        text_translation="O Allah, send blessings upon Muhammad and the family of Muhammad, as You sent blessings upon Ibrahim and the family of Ibrahim. Indeed, You are Praiseworthy, Glorious.",
        time_of_day=TimeOfDay.morning,
        source="Sahih al-Bukhari 3370 — the salawat taught by the Prophet (PBUH)",
        repeat_count=1,
    ),
    # -----------------------------------------------------------------------
    # A'UDHU BIKALIMATILLAHI TAMMATI
    # -----------------------------------------------------------------------
    Adhkar(
        text_arabic="أَعُوذُ بِكَلِمَاتِ اللَّهِ التَّامَّاتِ مِنْ شَرِّ مَا خَلَقَ",
        text_translation="I seek refuge in the perfect words of Allah from the evil of what He has created.",
        time_of_day=TimeOfDay.morning,
        source="Sahih Muslim 2709 — recited 3x in the evening, also recommended in the morning",
        repeat_count=3,
    ),
]

print(f"Seeding {len(entries)} adhkar entries...")
for entry in entries:
    db.add(entry)
db.commit()
print("Adhkar seeded successfully.")
