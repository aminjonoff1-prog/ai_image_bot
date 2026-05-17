import httpx
import asyncio
import json
import base64
import google.generativeai as genai
# config.py dan GEMINI_API_KEY import qilish
try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = None

# Lyria 3 Clip modelining REST API endpointi
LYRIA_MODEL = "lyria-3-clip-preview"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
GENERATE_URL = f"{BASE_URL}/models/{LYRIA_MODEL}:generateContent"

# Matnli Gemini modeli faqat prompt yozishga yordam beradi
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
    gemini_text_model = genai.GenerativeModel('gemini-1.5-pro-latest')

async def process_audio_prompt(user_text):
    """
    Foydalanuvchi g'oyasini Gemini yordamida Lyria uchun professional promptga aylantiradi.
    """
    if not GEMINI_API_KEY:
        # API kalit bo'lmasa, bazaviy inglizcha prompt qaytaramiz
        return f"Generate a high-quality 30-second studio track based on: {user_text}"

    system_prompt = (f"Sen professional bastakor va saund-dizaynersan. "
                     f"Foydalanuvchi musiqa yaratmoqchi: '{user_text}'. "
                     f"Shu g'oyani Google Lyria 3 modeli tushunadigan, janr, temp, instrumentlar "
                     f"va emotsional kayfiyat aniq ko'rsatilgan professional inglizcha musiqa promptiga aylantir. "
                     f"Faqat inglizcha promptni o'zini qaytar, hech qanday izoh yozma.")
    try:
        # Matn generatorini asinxron ipda ishlatamiz
        response = await asyncio.to_thread(gemini_text_model.generate_content, system_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Prompt processing error: {e}")
        # Xatolik bo'lsa, foydalanuvchi matniga bazaviy inglizcha qo'shimcha qilamiz
        return f"Studio quality background track about: {user_text}"

async def generate_audio(prompt_text):
    """
    Haqiqiy musiqa generatsiyasini Lyria REST API orqali amalga oshiradi.
    """
    if not GEMINI_API_KEY:
        return None, "API kalit topilmadi. configuratsiyani tekshiring."

    # Professional promptni tayyorlaymiz
    final_english_prompt = await process_audio_prompt(prompt_text)
    print(f"Final Lyria Prompt: {final_english_prompt}")

    # Gemini API uchun kerakli sarlavhalar (Header)
    headers = {
        "x-goog-api-key": GEMINI_API_KEY.strip(), # To'g'ri autentifikatsiya
        "Content-Type": "application/json"
    }

    # Gemini REST API standart JSON strukturasi
    payload = {
        "contents": [
            {
                "parts": [
                    {"text": final_english_prompt}
                ]
            }
        ]
    }

    try:
        # httpx asinxron klienti yordamida so'rov yuboramiz
        async with httpx.AsyncClient(timeout=180) as client: # Lyria biroz sekinroq, timeout ko'proq
            response = await client.post(GENERATE_URL, headers=headers, json=payload)
            
            if response.status_code == 200:
                result_json = response.json()
                
                # API odatda audio ma'lumotni Base64 formatida JSON ichida qaytaradi
                # JSON strukturasini parse qilib audio qismini topamiz
                try:
                    # Odatda struktura: result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    audio_b64_data = result_json['candidates'][0]['content']['parts'][0]['inlineData']['data']
                    
                    # Base64 dan baytlargacha dekodlaymiz
                    audio_bytes = base64.b64decode(audio_b64_data)
                    
                    # Faylni saqlaymiz
                    filename = f"lyria_audio_{hash(prompt_text)}.mp3"
                    with open(filename, "wb") as f:
                        f.write(audio_bytes)
                        
                    print(f"✅ Audio saqlandi: {filename}")
                    return filename, None
                    
                except (KeyError, IndexError, ValueError) as parse_error:
                    return None, f"API javobini parse qilishda xatolik: {parse_error}"
            
            # Agar xato kod qaytsa, javob tanasini o'qiymiz
            try:
                error_details = response.json()
                error_msg = error_details.get('error', {}).get('message', f"Status code: {response.status_code}")
            except Exception:
                error_msg = f"Status code: {response.status_code}"
                
            return None, f"Lyria API Xatosi: {error_msg}"
            
    except httpx.RequestError as e:
        return None, f"Tarmoq xatoligi: {e}"
    except Exception as e:
        return None, f"Kutilmagan xatolik: {e}"
