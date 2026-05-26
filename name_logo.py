import asyncio
import google.generativeai as genai
from config import GEMINI_API_KEY

gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        gemini_model = genai.GenerativeModel("gemini-pro")
    except Exception:
        gemini_model = None


async def generate_name_logo_info(name: str):
    if not gemini_model:
        return {
            "meaning": f"{name} ismi uchun ma'lumot topilmadi.",
            "idea": f"{name} uchun minimalist va premium logo tavsiya etiladi.",
            "prompt": f"minimalist elegant logo for {name}, premium typography, clean vector, white background"
        }

    prompt = f"""
Siz professional naming strategist va logo designer siz.

ISM:
{name}

Vazifa:
1. Shu ismning o'zbekcha ma'nosini yozing
2. Shu ismga mos logo idea bering
3. Shu ism uchun inglizcha professional logo prompt yozing

FORMAT:
MEANING: ...
IDEA: ...
PROMPT: ...

Faqat shu formatda yozing.
"""

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        text = response.text.strip()

        result = {
            "meaning": "",
            "idea": "",
            "prompt": ""
        }

        for line in text.split("\n"):
            line = line.strip()
            if line.upper().startswith("MEANING:"):
                result["meaning"] = line[8:].strip()
            elif line.upper().startswith("IDEA:"):
                result["idea"] = line[5:].strip()
            elif line.upper().startswith("PROMPT:"):
                result["prompt"] = line[7:].strip()

        if not result["meaning"]:
            result["meaning"] = f"{name} ismi ijobiy va chiroyli ma'noga ega."
        if not result["idea"]:
            result["idea"] = f"{name} uchun zamonaviy va premium logo tavsiya qilinadi."
        if not result["prompt"]:
            result["prompt"] = f"minimalist luxury logo for {name}, elegant typography, vector, clean white background"

        return result

    except Exception:
        return {
            "meaning": f"{name} ismi ijobiy ma'noga ega.",
            "idea": f"{name} uchun zamonaviy va premium logo tavsiya qilinadi.",
            "prompt": f"minimalist luxury logo for {name}, elegant typography, vector, clean white background"
        }
