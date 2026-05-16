import httpx
import asyncio
import google.generativeai as genai
from config import GEMINI_API_KEY

LYRIA_URL = "https://api.google.ai/v1/lyria:generateMusic"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

async def process_audio_prompt(user_text):
    if not GEMINI_API_KEY:
        return user_text + ", professional arrangement, high fidelity, 320kbps"

    system_prompt = (f"Sen professional bastakor va saund-dizaynersan. "
                     f"Foydalanuvchi musiqa yaratmoqchi: '{user_text}'. "
                     f"Shu g'oyani Google Lyria 3 modeli tushunadigan, janr, temp, instrumentlar "
                     f"va emotsional kayfiyat aniq ko'rsatilgan professional inglizcha musiqa promptiga aylantir. "
                     f"Faqat inglizcha promptni o'zini qaytar, hech qanday izoh yozma.")
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, system_prompt)
        return response.text.strip()
    except Exception:
        return user_text + ", high quality studio background track"

async def generate_audio(prompt):
    if not GEMINI_API_KEY:
        return None, "API kalit topilmadi."

    final_prompt = await process_audio_prompt(prompt)
    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY.strip()}",
        "Content-Type": "application/json"
    }
    data = {
        "prompt": final_prompt,
        "duration_seconds": 30
    }

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(LYRIA_URL, headers=headers, json=data)
            if r.status_code == 200:
                filename = f"audio_{hash(prompt)}.mp3"
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename, None
            return None, f"Lyria API xatosi: {r.status_code}"
    except Exception as e:
        return None, str(e)
