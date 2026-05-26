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
# GEMINI MODEL (sinxron test QILMAYMIZ)
# ============================================================

MODELS = [
    "gemini-2.0-flash",
    "gemini-1.5-flash",
    "gemini-1.5-pro",
    "gemini-pro",
]


async def safe_gemini_call(prompt: str) -> str:
    """Xavfsiz va tez Gemini chaqiruv. Bot qotmaydi."""
    if not GEMINI_API_KEY:
        return None

    for model_name in MODELS:
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
# HARF VA JINS TIZIMI
# ============================================================

LETTER_STYLES = {
    "A": {"shape": "triangle, arrow", "color": "royal blue and gold", "feel": "leadership"},
    "B": {"shape": "bold curves, book", "color": "burgundy and cream", "feel": "stability"},
    "C": {"shape": "crescent, crown", "color": "coral and silver", "feel": "creativity"},
    "D": {"shape": "diamond, dome", "color": "deep purple and gold", "feel": "dignity"},
    "E": {"shape": "eagle, energy wave", "color": "emerald green and white", "feel": "energy"},
    "F": {"shape": "flame, feather", "color": "orange and dark gray", "feel": "freedom"},
    "G": {"shape": "globe, geometric", "color": "green and gold", "feel": "growth"},
    "H": {"shape": "pillar, horizon", "color": "navy and silver", "feel": "honor"},
    "I": {"shape": "pillar, infinity", "color": "indigo and white", "feel": "intelligence"},
    "J": {"shape": "jewel, jade", "color": "jade green and gold", "feel": "joy"},
    "K": {"shape": "key, knight shield", "color": "black and gold", "feel": "knowledge"},
    "L": {"shape": "leaf, laurel", "color": "lime and dark green", "feel": "loyalty"},
    "M": {"shape": "mountain, mosaic", "color": "dark navy and gold", "feel": "mastery"},
    "N": {"shape": "north star", "color": "navy blue and silver", "feel": "nobility"},
    "O": {"shape": "orbit, olive branch", "color": "orange and white", "feel": "optimism"},
    "P": {"shape": "phoenix, pearl", "color": "purple and gold", "feel": "power"},
    "Q": {"shape": "queen crown, quill", "color": "gold and dark red", "feel": "quality"},
    "R": {"shape": "ribbon, royal crest", "color": "red and gold", "feel": "royalty"},
    "S": {"shape": "shield, sun", "color": "sapphire blue and gold", "feel": "strength"},
    "T": {"shape": "tower, tree", "color": "teal and bronze", "feel": "trust"},
    "U": {"shape": "unity symbol", "color": "ultramarine and white", "feel": "unity"},
    "V": {"shape": "victory wings", "color": "violet and silver", "feel": "valor"},
    "W": {"shape": "wave, wings", "color": "wine red and gold", "feel": "wisdom"},
    "X": {"shape": "abstract geometric", "color": "black and electric blue", "feel": "excellence"},
    "Y": {"shape": "tree branch", "color": "yellow gold and green", "feel": "youth"},
    "Z": {"shape": "zigzag, zen circle", "color": "azure blue and gold", "feel": "zeal"},
}

FEMALE_ENDINGS = ["a", "o", "i", "gul", "noz", "oy", "xon", "bibi", "begim"]
MALE_ENDINGS = ["on", "od", "id", "ur", "ul", "bek", "boy", "ali", "jon", "din"]


def detect_gender(name: str) -> str:
    lower = name.lower().strip()
    for e in FEMALE_ENDINGS:
        if lower.endswith(e):
            return "female"
    for e in MALE_ENDINGS:
        if lower.endswith(e):
            return "male"
    return "neutral"


def generate_smart_default(name: str) -> dict:
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

    meaning = (
        f"{name_clean} — bu {g_desc} xususiyatlarni o'zida "
        f"mujassam etgan go'zal va ma'noli ism. "
        f"Bu ism o'z egasiga yuksak maqsadlar, ezgulik va muvaffaqiyat tilaydigan "
        f"chuqur ma'noga ega. '{first}' harfi bilan boshlanishi "
        f"{style['feel']} kabi fazilatlarni anglatadi. "
        f"Bu ismni tashuvchi inson jamiyatda hurmat va e'tiborga sazovor bo'ladi."
    )

    idea = (
        f"'{name_clean}' uchun {g_style} uslubda premium monogram logo tavsiya etiladi. "
        f"'{first}' harfi {style['shape']} elementlari bilan birlashtiriladi. "
        f"Ranglar: {style['color']}. "
        f"Logo {g_elem} qo'shilgan holda zamonaviy ko'rinishga ega bo'ladi."
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

    # 1. Gemini dan so'rash (15 sekund timeout)
    if GEMINI_API_KEY:
        prompt = f"""
Sen onomastika (ismlar ilmi) professori va logo dizaynersiz.

ISM: "{name}"

VAZIFA:
1. MEANING: Ismning kelib chiqishi, qaysi tildan ekanligi, lug'aviy ma'nosi, qanday xususiyatlarni anglatishi — o'zbek tilida batafsil (4-5 jumla)

2. IDEA: Ismga mos logo g'oyasi — shakl, element, ranglar, uslub — o'zbek tilida (3-4 jumla)

3. PROMPT: Stability AI uchun inglizcha logo prompt (1 uzun jumla)

FORMAT:
MEANING: [ma'no]
IDEA: [g'oya]
PROMPT: [prompt]
"""

        try:
            text = await safe_gemini_call(prompt)

            if text:
                result = {"meaning": "", "idea": "", "prompt": ""}
                current_key = None
                lines_buf = []

                for line in text.split("\n"):
                    s = line.strip()
                    if not s:
                        continue

                    if s.upper().startswith("MEANING:"):
                        if current_key and lines_buf:
                            result[current_key] = " ".join(lines_buf)
                        current_key = "meaning"
                        lines_buf = [s[8:].strip()]

                    elif s.upper().startswith("IDEA:"):
                        if current_key and lines_buf:
                            result[current_key] = " ".join(lines_buf)
                        current_key = "idea"
                        lines_buf = [s[5:].strip()]

                    elif s.upper().startswith("PROMPT:"):
                        if current_key and lines_buf:
                            result[current_key] = " ".join(lines_buf)
                        current_key = "prompt"
                        lines_buf = [s[7:].strip()]

                    elif current_key:
                        lines_buf.append(s)

                if current_key and lines_buf:
                    result[current_key] = " ".join(lines_buf)

                if result["meaning"] and result["prompt"]:
                    if not result["idea"]:
                        result["idea"] = f"{name} uchun zamonaviy logo tavsiya etiladi."
                    return result

        except Exception:
            pass

    # 2. Aqlli default
    return generate_smart_default(name)
