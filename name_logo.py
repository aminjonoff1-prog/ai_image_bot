import asyncio

try:
    import google.generativeai as genai
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY.strip())
except Exception:
    GEMINI_API_KEY = None


async def generate_name_logo_info(name: str) -> dict:
    default = {
        "meaning": f"{name} — chiroyli va ma'noli ism.",
        "idea": f"{name} uchun zamonaviy minimalist logo tavsiya etiladi.",
        "prompt": f"minimalist elegant monogram logo for '{name}', premium typography, clean vector, white background, gold and dark navy colors"
    }

    if not GEMINI_API_KEY:
        return default

    prompt = f"""
Siz professional naming strategist va logo dizaynersiz.

ISM: {name}

Vazifa:
1. Shu ismning ma'nosini o'zbek tilida yozing (2-3 jumla)
2. Shu ismga mos logo g'oyasini o'zbek tilida yozing (2-3 jumla)
3. Shu ism uchun inglizcha Stability AI logo prompt yozing (1 jumla)

FORMAT:
MEANING: [o'zbekcha ma'no]
IDEA: [o'zbekcha logo g'oyasi]
PROMPT: [inglizcha logo prompt]

Faqat shu formatda yozing. Ortiqcha so'z yozmang.
"""

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = await asyncio.to_thread(model.generate_content, prompt)
        text = response.text.strip()

        result = {"meaning": "", "idea": "", "prompt": ""}

        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("MEANING:"):
                result["meaning"] = line[8:].strip()
            elif line.upper().startswith("IDEA:"):
                result["idea"] = line[5:].strip()
            elif line.upper().startswith("PROMPT:"):
                result["prompt"] = line[7:].strip()

        if not result["meaning"]:
            result["meaning"] = default["meaning"]
        if not result["idea"]:
            result["idea"] = default["idea"]
        if not result["prompt"]:
            result["prompt"] = default["prompt"]

        return result

    except Exception as e:
        print(f"Name logo xatosi: {e}")
        return default
