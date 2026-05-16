import httpx
import asyncio
import google.generativeai as genai
from config import GEMINI_API_KEY

# Google Veo API manzili
VEO_URL = "https://api.google.ai/v1/veo:generateVideo"

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# --- GEMINI YORDAMIDA REJISSYORLIK PROMTI YARATISH ---
async def process_video_prompt(user_text):
    if not GEMINI_API_KEY:
        return user_text + ", cinematic lighting, 4k resolution, smooth motion"

    system_prompt = (f"Sen professional kinematograf va rejissyorsan. "
                     f"Foydalanuvchi video yaratmoqchi: '{user_text}'. "
                     f"Shu g'oyani Google Veo modeli tushunadigan, kamera harakatlari (pan, tilt, zoom), "
                     f"kadr tabiati, yorug'lik effektlari va tabiiy audio foni (natively generated audio cues) "
                     f"kiritilgan mukammal INGLIZ tilidagi video-promptga aylantirib ber. "
                     f"Faqat inglizcha promptni o'zini qaytar, hech qanday izoh yozma.")
    
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, system_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Video Prompt xatosi: {e}")
        return user_text + ", high quality cinematic video, 4k, smooth transition"

# --- GOOGLE VEO ORQALI VIDEO YARATISH ---
async def generate_video(prompt):
    if not GEMINI_API_KEY:
        return None, "Gemini/Veo API kaliti topilmadi."

    final_prompt = await process_video_prompt(prompt)
    print(f"Generatsiya qilinayotgan VIDEO PROMPT: {final_prompt}")

    headers = {
        "Authorization": f"Bearer {GEMINI_API_KEY.strip()}",
        "Content-Type": "application/json"
    }

    # Veo modeli uchun konfiguratsiya (Matndan videoga va audio qo'shish)
    data = {
        "prompt": final_prompt,
        "aspect_ratio": "16:9",
        "include_audio": True,  # Tabiiy ovoz effektlarini yoqish
        "duration_seconds": 5   # Standart yuqori sifatli davomiylik
    }

    try:
        # Video generatsiyasi vaqt talab qilishi mumkin (timeout 180 soniya)
        async with httpx.AsyncClient(timeout=180) as client:
            r = await client.post(VEO_URL, headers=headers, json=data)

            if r.status_code == 200:
                filename = f"video_{hash(prompt)}.mp4"
                # API dan qaytgan tayyor video kontentini bayner ko'rinishida yozamiz
                with open(filename, "wb") as f:
                    f.write(r.content)
                return filename, None
            
            return None, f"Veo API xatosi ({r.status_code}): {r.text[:100]}"
            
    except Exception as e:
        return None, f"Tizim xatoligi: {str(e)}"
