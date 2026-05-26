import httpx
import asyncio
import uuid

from deep_translator import GoogleTranslator

# Yangi rasmiy Google GenAI SDK importi
try:
    from google import genai
    from google.genai import types
    from config import GEMINI_API_KEY
    
    if GEMINI_API_KEY and GEMINI_API_KEY.strip():
        # Yangi kutubxonada Client asinxron rejim (aio) uchun quyidagicha yaratiladi
        ai_client = genai.Client(api_key=GEMINI_API_KEY.strip())
    else:
        ai_client = None
except Exception as e:
    print(f"Gemini SDK yuklashda xato: {e}")
    ai_client = None

from config import STABILITY_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

CATEGORY = {
    "🎨 Logo": "professional modern minimalist logo, vector, clean design, white background",
    "🖼 Realistik": "ultra realistic photo, photorealistic, natural lighting, highly detailed, 8k",
    "📱 Avatar": "professional portrait avatar, profile picture, detailed face, studio lighting",
    "🏠 Interyer": "professional interior design, photorealistic room, modern furniture, cozy",
    "🌄 Landscape": "epic realistic landscape photography, nature, cinematic, detailed",
    "🖥 UI/UX Web Dizayn": "professional UI/UX web design, landing page, modern, figma style",
    "🏢 3D Arxitektura": "highly detailed 3D architecture render, modern building, realistic",
    "💎 Brending": "brand identity mockup, elegant branding, premium business design",
    "🎮 Konsept Art": "epic concept art, cinematic composition, highly detailed, artstation",
    "🏢 Reklama Banneri": "advertising banner background, clean composition, empty text area",
}

NEGATIVE_PROMPT = (
    "wrong subject, unrelated object, extra objects, distorted, deformed, "
    "low quality, blurry, watermark, text, letters, duplicate, ugly"
)

# Yangi tavsiya etilgan Gemini modellari ro'yxati
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash",
]


def translate_uz_to_en(text: str) -> str:
    """O'zbekchadan inglizchaga aniq tarjima"""
    try:
        result = GoogleTranslator(source='uz', target='en').translate(text)
        if result and result.strip():
            return result.strip()
    except Exception:
        pass

    try:
        result = GoogleTranslator(source='auto', target='en').translate(text)
        if result and result.strip():
            return result.strip()
    except Exception:
        pass

    return text


async def enhance_prompt(english_text: str, category: str) -> str:
    """Yangi google-genai (asinxron) orqali promptni boyitadi. 10 sekund timeout."""
    if not ai_client:
        return english_text

    base_style = CATEGORY.get(category, "")

    system_prompt = (
        f'The user wants an image of: "{english_text}"\n'
        f'Category: "{base_style}"\n'
        f'Keep the main subject EXACTLY. Add only visual details.\n'
        f'Return only the final prompt. Max 2 sentences.'
    )

    for model_name in GEMINI_MODELS:
        try:
            # Yangi SDKda asinxron chaqiruv: ai_client.aio.models.generate_content
            response = await asyncio.wait_for(
                ai_client.aio.models.generate_content(
                    model=model_name,
                    contents=system_prompt
                ),
                timeout=10.0
            )
            result = (response.text or "").strip()
            if result:
                return result
        except asyncio.TimeoutError:
            print(f"Gemini {model_name} timeout berdi, keyingisiga o'tilmoqda...")
            continue
        except Exception as e:
            print(f"Gemini {model_name} xatolik: {e}, keyingisiga o'tilmoqda...")
            continue

    return english_text


async def process_prompt(user_text: str, category: str):
    """Prompt yaratish: tarjima + boyitish + himoya"""
    user_text = user_text.strip()

    if not user_text:
        return None, "Prompt bo'sh bo'lmasligi kerak."

    base_style = CATEGORY.get(category, "")

    # 1. Tarjima (timeout 8 sekund)
    try:
        english_text = await asyncio.wait_for(
            asyncio.to_thread(translate_uz_to_en, user_text),
            timeout=8.0
        )
    except asyncio.TimeoutError:
        english_text = user_text

    print(f"ORIGINAL: {user_text}")
    print(f"TRANSLATED: {english_text}")

    # 2. Gemini bilan boyitish (timeout 10 sekund)
    enhanced = await enhance_prompt(english_text, category)

    print(f"ENHANCED: {enhanced}")

    # 3. Final prompt
    final_prompt = (
        f"{enhanced}, {base_style}. "
        f"The image must clearly show: {english_text}. "
        f"Do not change the main subject."
    )

    if category == "🏢 Reklama Banneri":
        final_prompt += ", no text, no letters, large empty space for typography"

    print(f"FINAL: {final_prompt}")

    return final_prompt, None


async def generate_image(prompt: str, category: str):
    """Stability AI orqali rasm yaratish"""
    api_key = STABILITY_API_KEY.strip() if STABILITY_API_KEY else ""

    if not api_key:
        return None, "STABILITY_API_KEY topilmadi."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    final_prompt, err = await process_prompt(prompt, category)
    if err:
        return None, err

    aspect_ratio = "16:9"
    if category in ["🎨 Logo", "💎 Brending"]:
        aspect_ratio = "1:1"
    elif category in ["📱 Avatar"]:
        aspect_ratio = "9:16"

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                URL,
                headers=headers,
                data={
                    "prompt": final_prompt,
                    "negative_prompt": NEGATIVE_PROMPT,
                    "output_format": "png",
                    "aspect_ratio": aspect_ratio
                },
                files={"none": ("", b"")}
            )

        if r.status_code == 200:
            filename = f"temp_{uuid.uuid4().hex}.png"
            with open(filename, "wb") as f:
                f.write(r.content)
            return filename, None

        return None, f"Xato ({r.status_code}): {r.text[:200]}"

    except httpx.TimeoutException:
        return None, "Rasm yaratish vaqti tugadi. Qayta urinib ko'ring."
    except Exception as e:
        return None, f"Kutilmagan xato: {e}"
