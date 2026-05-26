import httpx
import asyncio
import uuid

from deep_translator import GoogleTranslator

try:
    import google.generativeai as genai
    from config import GEMINI_API_KEY
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY.strip())
except Exception:
    GEMINI_API_KEY = None

from config import STABILITY_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

# Kategoriya uslublari
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


def translate_uz_to_en(text: str) -> str:
    """O'zbekchadan inglizchaga ANIQ tarjima"""
    try:
        translated = GoogleTranslator(source='uz', target='en').translate(text)
        if translated:
            return translated.strip()
    except Exception as e:
        print(f"Tarjima xatosi: {e}")

    # Fallback: avtomatik til aniqlash
    try:
        translated = GoogleTranslator(source='auto', target='en').translate(text)
        if translated:
            return translated.strip()
    except Exception:
        pass

    return text


async def enhance_prompt(english_text: str, category: str) -> str:
    """Gemini bilan promptni boyitadi (ixtiyoriy)"""
    if not GEMINI_API_KEY:
        return english_text

    base_style = CATEGORY.get(category, "")

    system_prompt = f"""
You are a professional AI image prompt engineer.

The user wants an image of:
"{english_text}"

Category style:
"{base_style}"

RULES:
1. Keep the main subject EXACTLY as described
2. Do NOT change or replace the subject
3. Add only visual details: lighting, camera angle, composition
4. Keep it short (max 2 sentences)
5. Return only the final prompt

Final prompt:
"""

    try:
        model = genai.GenerativeModel("gemini-pro")
        response = await asyncio.to_thread(model.generate_content, system_prompt)
        result = response.text.strip()
        if result:
            return result
    except Exception as e:
        print(f"Gemini enhance xatosi: {e}")

    return english_text


async def process_prompt(user_text: str, category: str):
    """To'liq prompt yaratish jarayoni"""
    user_text = user_text.strip()

    if not user_text:
        return None, "Prompt bo'sh bo'lmasligi kerak."

    base_style = CATEGORY.get(category, "")

    # 1-QADAM: O'zbekchadan inglizchaga ANIQ tarjima
    english_text = await asyncio.to_thread(translate_uz_to_en, user_text)

    print(f"ORIGINAL: {user_text}")
    print(f"TRANSLATED: {english_text}")

    # 2-QADAM: Gemini bilan boyitish (ixtiyoriy)
    enhanced = await enhance_prompt(english_text, category)

    print(f"ENHANCED: {enhanced}")

    # 3-QADAM: Asosiy obyektni saqlash
    final_prompt = (
        f"{enhanced}, {base_style}. "
        f"The image must clearly show: {english_text}. "
        f"Do not change the main subject."
    )

    # Banner uchun maxsus
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

    # Aspect ratio
    aspect_ratio = "16:9"
    if category in ["🎨 Logo", "💎 Brending"]:
        aspect_ratio = "1:1"
    elif category in ["📱 Avatar"]:
        aspect_ratio = "9:16"

    async with httpx.AsyncClient(timeout=180) as client:
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
