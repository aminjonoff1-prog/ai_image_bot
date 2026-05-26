import asyncio
import os

from deep_translator import GoogleTranslator

try:
    import google.generativeai as genai
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY.strip())
except Exception:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]


# ============================================================
# 100+ O'ZBEK ISMLARI BAZASI
# ============================================================

NAMES_DB = {
    # ERKAKLAR
    "muhammad": "Muhammad — arabcha 'maqtovga sazovor, hamd etilgan'. Islom payg'ambari nomi. Eng ulug' va muqaddas ismlardan biri.",
    "muhammadamin": "Muhammadamin — arabcha 'maqtovga sazovor va ishonchli'. Muhammad (maqtalgan) + Amin (ishonchli, sadoqatli).",
    "abdulloh": "Abdulloh — arabcha 'Allohning bandasi'. Kamtarlik va ibodat ma'nosini anglatadi.",
    "ahmad": "Ahmad — arabcha 'eng maqtovga loyiq'. Muhammad payg'ambarning yana bir ismi.",
    "ali": "Ali — arabcha 'yuksak, baland, ulug''. Hazrati Ali — to'rtinchi xalifa nomi.",
    "umar": "Umar — arabcha 'hayot, umr'. Hazrati Umar — ikkinchi xalifa nomi.",
    "usmon": "Usmon — arabcha 'ilon bolasi' yoki 'yosh'. Hazrati Usmon — uchinchi xalifa.",
    "islom": "Islom — arabcha 'tinchlik, itoatkorlik'. Islom dini nomi bilan bog'liq.",
    "jasur": "Jasur — o'zbekcha 'jasoratli, botir, qo'rqmas'. Mardlik va kuch ramzi.",
    "sherzod": "Sherzod — forscha 'sher' (arslon) + 'zod' (tug'ilgan). 'Arslondan tug'ilgan'.",
    "temur": "Temur — turkcha 'temir, mustahkam, kuchli'. Amir Temur — buyuk sarkarda.",
    "bobur": "Bobur — turkcha-mo'g'ulcha 'yo'lbars, sher'. Zahiriddin Muhammad Bobur — buyuk shoh va shoir.",
    "sarvar": "Sarvar — forscha 'boshchi, yetakchi, sardor'. Rahbarlik va liderlik.",
    "javohir": "Javohir — arabcha 'javharlar, qimmatbaho toshlar'. Qadrlilik va noyoblik.",
    "dostonbek": "Dostonbek — turkcha 'do'st' + 'bek'. Do'stona va ulug' inson.",
    "firdavs": "Firdavs — forscha 'jannat bog'i'. Eng go'zal joy ma'nosida.",
    "husan": "Husan — arabcha 'go'zal, chiroyli'. Go'zallik va latofat.",
    "ilhom": "Ilhom — arabcha 'ilhomlanish, ruhlanish'. Ijodiy kuch va ilhom.",
    "jamshid": "Jamshid — forscha 'nurli, yorug'' + 'shoh'. Qadimgi Eron shohi nomi.",
    "kamoliddin": "Kamoliddin — arabcha 'dinning mukammalligi'. Barkamollik va yetuklik.",
    "laziz": "Laziz — arabcha 'yoqimli, totli, mazali'. Yoqimlililik.",
    "mirzo": "Mirzo — forscha 'shahzoda, amir o'g'li'. Olijanoblik va zotdorlik.",
    "nodir": "Nodir — arabcha 'kam topiluvchi, noyob'. Nodir va betakror.",
    "odil": "Odil — arabcha 'adolatli, to'g'ri'. Odillik va halollik.",
    "pulat": "Pulat — forscha 'po'lat, temir'. Mustahkamlik va kuch.",
    "ravshan": "Ravshan — forscha 'yorug', ravshan'. Nurlilik va tozalik.",
    "sanjar": "Sanjar — turkcha 'sanchmoq, o'tkir'. Sulton Sanjar — Saljuqiylar shohi.",
    "tohir": "Tohir — arabcha 'toza, pok, pokiza'. Poklik va tozalik.",
    "ulug'bek": "Ulug'bek — turkcha 'ulug'' + 'bek'. Mirzo Ulug'bek — buyuk olim va shoh.",
    "vohid": "Vohid — arabcha 'yagona, yolg'iz'. Yagonalik va tengsizlik.",
    "xurshid": "Xurshid — forscha 'quyosh'. Nurlilik va yorqinlik.",
    "yoqub": "Yoqub — ibroniycha 'iz bosuvchi'. Payg'ambar nomi.",
    "zafar": "Zafar — arabcha 'g'alaba'. Muvaffaqiyat va zafar.",
    "anvar": "Anvar — arabcha 'nurlar'. Yorqinlik va nurlilik.",
    "bahodir": "Bahodir — forscha 'bahodur, botir, jasur'. Kuch va jasorat.",
    "davron": "Davron — arabcha 'davr, zamon'. Zamonning eng yaxshi farzandi.",
    "eldor": "Eldor — turkcha 'el' + forscha 'dor'. Xalq faxri, el e'zozlagani.",
    "farhodjon": "Farhodjon — forscha 'farrux' (baxtli) + 'jon'. Baxtli va aziz.",
    "g'ayrat": "G'ayrat — arabcha 'shijoat, harakatchanlik'. Kuch va g'ayrat.",
    "hayot": "Hayot — arabcha 'tiriklik, yashash'. Hayot va umid ramzi.",
    "ikrom": "Ikrom — arabcha 'hurmat, izzat'. Hurmatlilik va sharaflilik.",
    "komil": "Komil — arabcha 'mukammal, barkamol'. Yetuklik.",
    "lochin": "Lochin — o'zbekcha 'lochin, qush'. Erkinlik va kuch.",
    "mansur": "Mansur — arabcha 'g'olib, zafar qozongan'. Muvaffaqiyat.",
    "narzullo": "Narzullo — arabcha 'Allohning nuri'. Ilohiy nur.",
    "otabek": "Otabek — turkcha 'ota' + 'bek'. Hurmatli, ulug'.",
    "rustam": "Rustam — forscha 'kuchli, bahodir'. Rustami Doston — pahlavon.",
    "saidakbar": "Saidakbar — arabcha 'said' (baxtli) + 'akbar' (buyuk). Buyuk va baxtli.",
    "umid": "Umid — forscha 'umid, orzu'. Kelajakka ishonch.",

    # AYOLLAR
    "zilola": "Zilola — forscha 'ziyoda, go'zal gul'. Nafislik va go'zallik ramzi.",
    "aziza": "Aziza — arabcha 'aziz, qadrli, hurmatli'. Qadr-qimmat va izzat.",
    "nodira": "Nodira — arabcha 'nodir, noyob'. O'zbek shoirasi Nodira nomi. Betakrorlik.",
    "dilnoza": "Dilnoza — forscha 'dil' (ko'ngil) + 'noz'. Ko'ngli nozik, nazokat egasi.",
    "gulnora": "Gulnora — forscha 'gul' + 'nur'. Guldek nurli, go'zal.",
    "malika": "Malika — arabcha 'malikah, qirolicha'. Hukmdor ayol, oliy martaba.",
    "kamola": "Kamola — arabcha 'komil, mukammal'. Barkamol va yetuk ayol.",
    "mohira": "Mohira — arabcha 'mohir, usta'. Mahoratli va iste'dodli.",
    "nafisa": "Nafisa — arabcha 'nafis, nozik, go'zal'. Nazokat va go'zallik.",
    "oydin": "Oydin — turkcha 'oy' + 'din'. Oyning nuri, yorug'lik.",
    "parvin": "Parvin — forscha 'Hulkar yulduzlari'. Nurli va go'zal.",
    "ra'no": "Ra'no — forscha 'rangin, go'zal'. Chiroylilik va jozibadorlik.",
    "sabohat": "Sabohat — arabcha 'go'zallik, chiroylilik'. Tashqi va ichki go'zallik.",
    "tabassum": "Tabassum — arabcha 'tabassum, kulgi'. Kulgulik va quvnoqlik.",
    "umida": "Umida — forscha 'umid, orzu'. Umid baxsh etuvchi.",
    "vasila": "Vasila — arabcha 'vosita, sabab'. Yaxshilikka sabab bo'luvchi.",
    "xilola": "Xilola — arabcha 'hilol, yangi oy'. Yangilik va go'zallik.",
    "yulduz": "Yulduz — turkcha 'yulduz, star'. Nurlilik va yo'l ko'rsatuvchi.",
    "zaynab": "Zaynab — arabcha 'otasining ziynati'. Payg'ambar qizi nomi.",
    "barno": "Barno — forscha 'yosh, navqiron, go'zal'. Yoshlik va go'zallik.",
    "charos": "Charos — forscha 'chiroyli, yoqimli'. Jozibadorlik.",
    "dilorom": "Dilorom — forscha 'dil' + 'orom'. Ko'ngilni tinchlantiruvchi.",
    "feruza": "Feruza — forscha 'firuza, ko'k qimmatbaho tosh'. Qimmatlilik.",
    "gavhar": "Gavhar — forscha 'javohir, qimmatbaho tosh'. Qadrlilik va noyoblik.",
    "hamida": "Hamida — arabcha 'maqtovga loyiq'. Yaxshi xulqli.",
    "iroda": "Iroda — arabcha 'iroda, xohish'. Kuchli iroda va maqsad.",
    "jamila": "Jamila — arabcha 'go'zal, chiroyli'. Go'zallik ramzi.",
    "kumush": "Kumush — turkcha 'kumush, silver'. Qimmatlilik. O'tkan kunlar qahramoni.",
    "latofat": "Latofat — arabcha 'latofat, nazokat'. Noziklik va nafislik.",
    "muazzam": "Muazzam — arabcha 'ulug', buyuk, azamatli'. Buyuklik.",
    "nasiba": "Nasiba — arabcha 'nasib, taqdir'. Baxtli taqdir.",
    "ozoda": "Ozoda — forscha 'ozod, erkin, toza'. Erkinlik va poklik.",
    "parizod": "Parizod — forscha 'pari' + 'zod'. Paridek go'zal.",
    "qunduz": "Qunduz — turkcha 'qunduz'. Mehribonlik va sadoqat.",
    "rohila": "Rohila — ibroniycha 'qo'zi, yumshoq'. Yumshoqlik va mehr.",
    "sarvinoz": "Sarvinoz — forscha 'sarv' (daraxt) + 'noz'. Sarv qomatli nozanin.",
    "turgunoy": "Turgunoy — turkcha 'turgun' + 'oy'. Doimiy va go'zal.",
    "ulmas": "Ulmas — turkcha 'o'lmas, abadiy'. Abadiylik va uzoq umr.",
    "venera": "Venera — lotincha 'go'zallik ma'budasi'. Jozibadorlik.",
    "shaxlo": "Shaxlo — forscha 'shoh' + 'la'l'. Qirollik go'zalligi.",
    "zulayho": "Zulayho — arabcha 'go'zal, latif'. Yusuf va Zulayho dostonidagi go'zal.",
    "maftuna": "Maftuna — arabcha 'maftun, sehrlanuvchi'. Sehrli go'zallik.",
    "dildora": "Dildora — forscha 'dil' + 'dor'. Ko'ngil egasi, sevimli.",
    "sevinch": "Sevinch — o'zbekcha 'quvonch, shodlik'. Quvnoqlik va baxt.",
    "madina": "Madina — arabcha 'shahar'. Muqaddas shahar Madina nomi.",
    "fatima": "Fatima — arabcha 'ko'krakdan ajralgan'. Payg'ambar qizi nomi.",
    "oisha": "Oisha — arabcha 'tirik, hayotchan'. Payg'ambar rafiqasi nomi.",
    "marjona": "Marjona — arabcha 'marjon, marvarid'. Qimmatbaho va noyob.",
    "shahzoda": "Shahzoda — forscha 'shoh' + 'zod'. Shohona zotdan bo'lgan.",
    "nilufar": "Nilufar — forscha 'nilufar guli'. Poklik va go'zallik ramzi.",
    "mohichehra": "Mohichehra — forscha 'moh' (oy) + 'chehr' (yuz). Oydek yuzli go'zal.",
    "binafsha": "Binafsha — forscha 'binafsha guli'. Nafislik va kamtarlik.",
    "bahora": "Bahora — forscha 'bahor'. Bahor fasli, yangilanish va go'zallik.",
    "oygul": "Oygul — turkcha 'oy' + forscha 'gul'. Oydek go'zal gul.",
    "saodat": "Saodat — arabcha 'saodat, baxt'. Baxtiyorlik va farovonlik.",
}


# ============================================================
# GEMINI CHAQIRUV (xavfsiz va tez)
# ============================================================

async def safe_gemini_call(prompt: str) -> str:
    if not GEMINI_API_KEY:
        return None

    for model_name in GEMINI_MODELS:
        try:
            model = genai.GenerativeModel(model_name)
            response = await asyncio.wait_for(
                asyncio.to_thread(model.generate_content, prompt),
                timeout=15.0
            )
            text = (response.text or "").strip()
            if text:
                return text
        except asyncio.TimeoutError:
            continue
        except Exception:
            continue

    return None


# ============================================================
# ISM MA'NOSINI TARJIMA ORQALI OLISH
# ============================================================

async def get_meaning_via_translate(name: str) -> str:
    """Google Translate orqali ism ma'nosini olishga harakat qiladi"""
    queries = [
        f"{name} ismi ma'nosi",
        f"{name} name meaning",
        f"meaning of the name {name}",
    ]

    for query in queries:
        try:
            result = await asyncio.wait_for(
                asyncio.to_thread(
                    GoogleTranslator(source='auto', target='uz').translate,
                    f"The name {name} means: "
                ),
                timeout=5.0
            )
            if result and len(result) > 10:
                return result
        except Exception:
            continue

    return None


# ============================================================
# JINS ANIQLASH VA DEFAULT
# ============================================================

FEMALE_ENDINGS = ["a", "o", "i", "gul", "noz", "oy", "xon", "bibi", "begim"]
MALE_ENDINGS = ["on", "od", "id", "ur", "ul", "bek", "boy", "ali", "jon", "din"]

LETTER_STYLES = {
    "A": {"shape": "triangle, arrow", "color": "royal blue and gold", "feel": "liderlik va intilish"},
    "B": {"shape": "bold curves, book", "color": "burgundy and cream", "feel": "barqarorlik va mehribonlik"},
    "C": {"shape": "crescent, crown", "color": "coral and silver", "feel": "ijodkorlik va joziba"},
    "D": {"shape": "diamond, dome", "color": "deep purple and gold", "feel": "qadr-qimmat va chuqurlik"},
    "E": {"shape": "eagle, energy wave", "color": "emerald green and white", "feel": "energiya va nafosatlilik"},
    "F": {"shape": "flame, feather", "color": "orange and dark gray", "feel": "erkinlik va ishtiyoq"},
    "G": {"shape": "globe, geometric", "color": "green and gold", "feel": "o'sish va saxovat"},
    "H": {"shape": "pillar, horizon", "color": "navy and silver", "feel": "sharaf va uyg'unlik"},
    "I": {"shape": "pillar, infinity", "color": "indigo and white", "feel": "aql va halollik"},
    "J": {"shape": "jewel, jade", "color": "jade green and gold", "feel": "quvonch va adolat"},
    "K": {"shape": "key, knight shield", "color": "black and gold", "feel": "bilim va kuch"},
    "L": {"shape": "leaf, laurel", "color": "lime and dark green", "feel": "hayot va sadoqat"},
    "M": {"shape": "mountain, mosaic", "color": "dark navy and gold", "feel": "mahorat va ulug'vorlik"},
    "N": {"shape": "north star", "color": "navy and silver", "feel": "olijanoblik va yo'l ko'rsatish"},
    "O": {"shape": "orbit, olive branch", "color": "orange and white", "feel": "ochiqlik va optimizm"},
    "P": {"shape": "phoenix, pearl", "color": "purple and gold", "feel": "qudrat va obro'"},
    "Q": {"shape": "queen crown, quill", "color": "gold and dark red", "feel": "sifat va mukammallik"},
    "R": {"shape": "ribbon, royal crest", "color": "red and gold", "feel": "shohona va chidamlilik"},
    "S": {"shape": "shield, sun", "color": "sapphire blue and gold", "feel": "kuch va zakovatlilik"},
    "T": {"shape": "tower, tree", "color": "teal and bronze", "feel": "ishonch va an'ana"},
    "U": {"shape": "unity symbol", "color": "ultramarine and white", "feel": "birlik va o'ziga xoslik"},
    "V": {"shape": "victory wings", "color": "violet and silver", "feel": "jasur va uzoqni ko'ruvchi"},
    "W": {"shape": "wave, wings", "color": "wine red and gold", "feel": "donolik va hayrat"},
    "X": {"shape": "abstract geometric", "color": "black and electric blue", "feel": "a'lochilik va favquloddalik"},
    "Y": {"shape": "tree branch", "color": "yellow gold and green", "feel": "yoshlik va intilish"},
    "Z": {"shape": "zigzag, zen circle", "color": "azure blue and gold", "feel": "g'ayrat va cho'qqi"},
}


def detect_gender(name: str) -> str:
    lower = name.lower().strip()
    for e in FEMALE_ENDINGS:
        if lower.endswith(e):
            return "female"
    for e in MALE_ENDINGS:
        if lower.endswith(e):
            return "male"
    return "neutral"


def generate_smart_default(name: str, extra_meaning: str = "") -> dict:
    name_clean = name.strip()
    first = name_clean[0].upper() if name_clean else "A"
    gender = detect_gender(name_clean)
    style = LETTER_STYLES.get(first, LETTER_STYLES["A"])

    if gender == "female":
        g_desc = "nafis, go'zal va nazik"
        g_style = "feminine elegant"
        g_elem = "flower petals, graceful curves"
    elif gender == "male":
        g_desc = "kuchli, jasur va ishonchli"
        g_style = "bold masculine"
        g_elem = "shield, strong geometric shapes"
    else:
        g_desc = "noyob, zamonaviy va professional"
        g_style = "modern unisex"
        g_elem = "clean geometric shapes"

    if extra_meaning:
        meaning = extra_meaning
    else:
        meaning = (
            f"{name_clean} — bu {g_desc} xususiyatlarni o'zida mujassam etgan "
            f"go'zal va ma'noli ism. Bu ism o'z egasiga yuksak maqsadlar, "
            f"ezgulik va muvaffaqiyat tilaydigan chuqur ma'noga ega. "
            f"'{first}' harfi bilan boshlanishi {style['feel']} "
            f"kabi fazilatlarni anglatadi."
        )

    idea = (
        f"'{name_clean}' uchun {g_style} uslubda premium monogram logo tavsiya etiladi. "
        f"'{first}' harfi {style['shape']} elementlari bilan birlashtiriladi. "
        f"Ranglar: {style['color']}. Logo {g_elem} qo'shilgan holda "
        f"zamonaviy va professional ko'rinishga ega bo'ladi."
    )

    prompt = (
        f"{g_style} premium monogram logo for '{name_clean}', "
        f"letter {first} with {style['shape']} elements, "
        f"{style['color']} colors, {g_elem}, "
        f"luxury brand, elegant typography, "
        f"vector design, clean white background"
    )

    return {"meaning": meaning, "idea": idea, "prompt": prompt}


# ============================================================
# ASOSIY FUNKSIYA
# ============================================================

async def generate_name_logo_info(name: str) -> dict:
    name = name.strip()
    if not name:
        return generate_smart_default("Ism")

    name_lower = name.lower().replace("'", "'").replace("ʻ", "'")

    # 1. BAZADAN TEKSHIRISH (eng tez)
    if name_lower in NAMES_DB:
        db_meaning = NAMES_DB[name_lower]

        first = name[0].upper()
        gender = detect_gender(name)
        style = LETTER_STYLES.get(first, LETTER_STYLES["A"])

        if gender == "female":
            g_style = "feminine elegant"
            g_elem = "flower petals, graceful curves"
        elif gender == "male":
            g_style = "bold masculine"
            g_elem = "shield, strong geometric shapes"
        else:
            g_style = "modern premium"
            g_elem = "clean geometric shapes"

        idea = (
            f"'{name}' uchun {g_style} uslubda monogram logo tavsiya etiladi. "
            f"'{first}' harfi {style['shape']} elementlari bilan birlashtiriladi. "
            f"Ranglar: {style['color']}."
        )

        prompt = (
            f"{g_style} premium monogram logo for '{name}', "
            f"letter {first} with {style['shape']} elements, "
            f"{style['color']} colors, {g_elem}, "
            f"luxury brand, elegant typography, vector, white background"
        )

        return {"meaning": db_meaning, "idea": idea, "prompt": prompt}

    # 2. GEMINI ORQALI (15 sekund timeout)
    if GEMINI_API_KEY:
        gemini_prompt = f"""
Sen onomastika professori va logo dizaynersiz.
ISM: "{name}"

O'zbek tilida yoz:
MEANING: Ismning kelib chiqishi, qaysi tildan, lug'aviy ma'nosi (4-5 jumla)
IDEA: Ismga mos logo g'oyasi — shakl, element, ranglar (3-4 jumla)
PROMPT: Stability AI uchun inglizcha logo prompt (1 jumla)

FORMAT:
MEANING: ...
IDEA: ...
PROMPT: ...
"""
        try:
            text = await safe_gemini_call(gemini_prompt)
            if text:
                result = {"meaning": "", "idea": "", "prompt": ""}
                current_key = None
                buf = []

                for line in text.split("\n"):
                    s = line.strip()
                    if not s:
                        continue
                    if s.upper().startswith("MEANING:"):
                        if current_key and buf:
                            result[current_key] = " ".join(buf)
                        current_key = "meaning"
                        buf = [s[8:].strip()]
                    elif s.upper().startswith("IDEA:"):
                        if current_key and buf:
                            result[current_key] = " ".join(buf)
                        current_key = "idea"
                        buf = [s[5:].strip()]
                    elif s.upper().startswith("PROMPT:"):
                        if current_key and buf:
                            result[current_key] = " ".join(buf)
                        current_key = "prompt"
                        buf = [s[7:].strip()]
                    elif current_key:
                        buf.append(s)

                if current_key and buf:
                    result[current_key] = " ".join(buf)

                if result["meaning"] and result["prompt"]:
                    if not result["idea"]:
                        result["idea"] = f"{name} uchun zamonaviy logo tavsiya etiladi."
                    return result
        except Exception:
            pass

    # 3. AQLLI DEFAULT
    return generate_smart_default(name)
