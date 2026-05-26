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


# ============================================================
# GEMINI MODEL TOPISH (bir marta topadi, keyin saqlab qo'yadi)
# ============================================================

_cached_model = None
_model_checked = False


def find_working_model():
    """Ishlaydigan Gemini modelini topadi va keshlab qo'yadi"""
    global _cached_model, _model_checked

    if _model_checked:
        return _cached_model

    models = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-pro",
        "gemini-1.5-pro-latest",
        "gemini-pro",
    ]

    for name in models:
        try:
            model = genai.GenerativeModel(name)
            # Test so'rov
            test = model.generate_content("Salom, 1+1 nechta?")
            if test and test.text:
                print(f"✅ Ism Logo uchun Gemini modeli topildi: {name}")
                _cached_model = model
                _model_checked = True
                return model
        except Exception as e:
            print(f"❌ Model ishlamadi: {name} -> {e}")
            continue

    print("⚠️ Hech qaysi Gemini modeli ishlamadi")
    _model_checked = True
    _cached_model = None
    return None


# ============================================================
# GEMINI ORQALI ISM MA'NOSI VA LOGO OLISH
# ============================================================

async def ask_gemini_about_name(name: str) -> dict:
    """Gemini dan ism haqida batafsil ma'lumot oladi"""
    model = await asyncio.to_thread(find_working_model)

    if not model:
        return None

    prompt = f"""
Sen dunyodagi eng bilimdon onomastika (ismlar ilmi) professori va professional logo dizaynersiz.

ISM: "{name}"

VAZIFA:
1. MEANING: Shu ismning kelib chiqishi (qaysi tildan: arab, fors, turk, o'zbek va h.k.), to'liq lug'aviy ma'nosi, qanday xususiyatlarni anglatishi — barchasini o'zbek tilida batafsil yoz (4-5 jumla). Agar ism noma'lum bo'lsa, harflar ma'nosini, fonetik jihatdan qanday his uyg'otishini yoz.

2. IDEA: Shu ismga mos professional logo g'oyasini o'zbek tilida batafsil yoz. Qanday shakl (monogram, emblem, geometric, abstract), qanday element (toj, qalqon, gul, yulduz, qilich va h.k.), qanday ranglar (aniq rang nomlari) ishlatilishi kerakligini yoz (3-4 jumla).

3. PROMPT: Shu ism uchun Stability AI ga beriladigan bitta batafsil inglizcha professional logo prompt yoz. Prompt ichida: logo turi, harflar, shakl, ranglar, uslub, fon — hammasi bo'lishi kerak (1 uzun jumla).

MUHIM QOIDALAR:
- Hech qanday ism "noma'lum" deb javob berma
- Har doim batafsil va ijobiy ma'lumot ber
- FORMAT qat'iy bo'lsin:

MEANING: [batafsil o'zbekcha ma'no]
IDEA: [batafsil o'zbekcha logo g'oyasi]
PROMPT: [batafsil inglizcha logo prompt]
"""

    try:
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()

        if not text:
            return None

        result = {"meaning": "", "idea": "", "prompt": ""}
        current_key = None
        current_lines = []

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            if stripped.upper().startswith("MEANING:"):
                if current_key and current_lines:
                    result[current_key] = " ".join(current_lines)
                current_key = "meaning"
                current_lines = [stripped[8:].strip()]

            elif stripped.upper().startswith("IDEA:"):
                if current_key and current_lines:
                    result[current_key] = " ".join(current_lines)
                current_key = "idea"
                current_lines = [stripped[5:].strip()]

            elif stripped.upper().startswith("PROMPT:"):
                if current_key and current_lines:
                    result[current_key] = " ".join(current_lines)
                current_key = "prompt"
                current_lines = [stripped[7:].strip()]

            elif current_key:
                current_lines.append(stripped)

        # Oxirgi qismni saqlash
        if current_key and current_lines:
            result[current_key] = " ".join(current_lines)

        # Tekshirish
        if result["meaning"] and result["prompt"]:
            if not result["idea"]:
                result["idea"] = f"{name} uchun zamonaviy va professional logo tavsiya etiladi."
            return result

        return None

    except Exception as e:
        print(f"Gemini ism xatosi: {e}")
        return None


# ============================================================
# DEEP TRANSLATOR ORQALI ISM MA'NOSI
# ============================================================

def translate_name_meaning(name: str) -> str:
    """Ism haqida Google Translate orqali qo'shimcha ma'lumot oladi"""
    try:
        # "X ismining ma'nosi" deb so'rab ko'ramiz
        query = f"{name} ismining ma'nosi nima"
        result = GoogleTranslator(source='uz', target='en').translate(query)
        if result:
            # Inglizchadan o'zbekchaga qaytaramiz
            back = GoogleTranslator(source='en', target='uz').translate(
                f"The name {name} is a beautiful name with positive meaning. "
                f"It represents strength, wisdom and kindness."
            )
            if back:
                return back
    except Exception:
        pass

    return ""


# ============================================================
# AQLLI DEFAULT TIZIMI
# ============================================================

# Harf xususiyatlari (har bir harf uchun uslub)
LETTER_STYLES = {
    "A": {"shape": "triangle, arrow, mountain peak", "color": "royal blue and gold", "feel": "leadership, ambition"},
    "B": {"shape": "bold curves, book, bridge", "color": "burgundy and cream", "feel": "stability, warmth"},
    "C": {"shape": "crescent, circle, crown", "color": "coral and silver", "feel": "creativity, charm"},
    "D": {"shape": "diamond, door, dome", "color": "deep purple and gold", "feel": "dignity, depth"},
    "E": {"shape": "three lines, eagle, energy wave", "color": "emerald green and white", "feel": "energy, elegance"},
    "F": {"shape": "flag, flame, feather", "color": "fiery orange and dark gray", "feel": "freedom, passion"},
    "G": {"shape": "globe, gear, geometric circle", "color": "green and gold", "feel": "growth, generosity"},
    "H": {"shape": "pillar, house, horizon", "color": "navy and silver", "feel": "honor, harmony"},
    "I": {"shape": "pillar, star, infinity", "color": "indigo and white", "feel": "intelligence, integrity"},
    "J": {"shape": "jewel, jade stone, curved hook", "color": "jade green and gold", "feel": "joy, justice"},
    "K": {"shape": "key, knight shield, kite", "color": "black and gold", "feel": "knowledge, strength"},
    "L": {"shape": "leaf, lightning, laurel wreath", "color": "lime green and dark green", "feel": "life, loyalty"},
    "M": {"shape": "mountain, monogram, mosaic", "color": "dark navy and gold", "feel": "mastery, magnificence"},
    "N": {"shape": "star, north star, nucleus", "color": "navy blue and silver", "feel": "nobility, navigation"},
    "O": {"shape": "circle, orbit, olive branch", "color": "orange and white", "feel": "openness, optimism"},
    "P": {"shape": "phoenix, pillar, pearl", "color": "purple and gold", "feel": "power, prestige"},
    "Q": {"shape": "queen crown, quill pen", "color": "gold and dark red", "feel": "quality, quintessence"},
    "R": {"shape": "ribbon, rose, royal crest", "color": "red and gold", "feel": "royalty, resilience"},
    "S": {"shape": "shield, serpent, sun", "color": "sapphire blue and gold", "feel": "strength, sophistication"},
    "T": {"shape": "tower, tree, triangle", "color": "teal and bronze", "feel": "trust, tradition"},
    "U": {"shape": "umbrella, unity symbol, upward arrow", "color": "ultramarine and white", "feel": "unity, uniqueness"},
    "V": {"shape": "victory wings, vine, chevron", "color": "violet and silver", "feel": "valor, vision"},
    "W": {"shape": "wave, wings, wreath", "color": "wine red and gold", "feel": "wisdom, wonder"},
    "X": {"shape": "cross, x-mark, abstract geometric", "color": "black and electric blue", "feel": "excellence, extraordinary"},
    "Y": {"shape": "tree branch, yacht sail, yin-yang", "color": "yellow gold and dark green", "feel": "youth, yearning"},
    "Z": {"shape": "zigzag, zen circle, zenith star", "color": "azure blue and gold", "feel": "zeal, zenith"},
}

# Ism oxiri bo'yicha jins aniqlash
FEMALE_ENDINGS = ["a", "o", "i", "gul", "noz", "oy", "zod", "xon", "bibi", "begim"]
MALE_ENDINGS = ["on", "od", "id", "ur", "ul", "bek", "boy", "ali", "jon", "din"]


def detect_gender(name: str) -> str:
    """Ismning jinsini taxmin qiladi"""
    lower = name.lower().strip()
    for ending in FEMALE_ENDINGS:
        if lower.endswith(ending):
            return "female"
    for ending in MALE_ENDINGS:
        if lower.endswith(ending):
            return "male"
    return "neutral"


def generate_smart_default(name: str) -> dict:
    """Gemini ishlamasa ham aqlli va batafsil javob beradi"""
    name_clean = name.strip()
    first_letter = name_clean[0].upper() if name_clean else "A"
    gender = detect_gender(name_clean)

    style = LETTER_STYLES.get(first_letter, LETTER_STYLES["A"])

    # Jinsga qarab so'zlar
    if gender == "female":
        gender_desc = "nafis, go'zal va nazik"
        gender_style = "feminine elegant"
        gender_elements = "flower petals, graceful curves"
    elif gender == "male":
        gender_desc = "kuchli, jasur va ishonchli"
        gender_style = "bold masculine"
        gender_elements = "shield, strong geometric shapes"
    else:
        gender_desc = "noyob, zamonaviy va professional"
        gender_style = "modern unisex"
        gender_elements = "clean geometric shapes"

    meaning = (
        f"{name_clean} — bu {gender_desc} xususiyatlarni o'zida "
        f"mujassam etgan go'zal va ma'noli ism. "
        f"Bu ism o'z egasiga yuksak maqsadlar, ezgulik va muvaffaqiyat "
        f"tilaydigan chuqur ma'noga ega. "
        f"'{first_letter}' harfi bilan boshlanishi {style['feel']} "
        f"kabi fazilatlarni anglatadi. "
        f"Bu ismni tashuvchi inson jamiyatda hurmat va e'tiborga sazovor bo'ladi."
    )

    idea = (
        f"'{name_clean}' uchun {gender_style} uslubda premium monogram logo tavsiya etiladi. "
        f"'{first_letter}' harfi {style['shape']} elementlari bilan birlashtiriladi. "
        f"Ranglar: {style['color']}. "
        f"Logo {gender_elements} qo'shilgan holda zamonaviy va professional "
        f"ko'rinishga ega bo'ladi."
    )

    prompt = (
        f"{gender_style} premium monogram logo for '{name_clean}', "
        f"featuring letter {first_letter} with {style['shape']} elements, "
        f"{style['color']} color scheme, {gender_elements}, "
        f"luxury brand identity, elegant refined typography, "
        f"professional vector design, clean white background, "
        f"high quality, minimalist yet sophisticated"
    )

    return {
        "meaning": meaning,
        "idea": idea,
        "prompt": prompt
    }


# ============================================================
# ASOSIY FUNKSIYA
# ============================================================

async def generate_name_logo_info(name: str) -> dict:
    """
    Har qanday ism uchun:
    1. Ma'nosini topadi
    2. Logo g'oyasini beradi
    3. Logo promptini yaratadi

    Ketma-ketlik:
    1. Gemini AI (eng yaxshi natija)
    2. Aqlli default (har doim ishlaydi)
    """

    name = name.strip()

    if not name:
        return generate_smart_default("Ism")

    # 1-QADAM: Gemini orqali so'rash
    if GEMINI_API_KEY:
        try:
            ai_result = await ask_gemini_about_name(name)
            if ai_result:
                print(f"✅ Gemini javob berdi: {name}")
                return ai_result
        except Exception as e:
            print(f"Gemini xatosi: {e}")

    # 2-QADAM: Aqlli default
    print(f"⚠️ Default ishlatilmoqda: {name}")
    return generate_smart_default(name)
