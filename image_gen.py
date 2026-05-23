import httpx
import asyncio
import uuid
import google.generativeai as genai
from config import STABILITY_API_KEY, GEMINI_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

# --- GEMINI SOZLAMALARI ---
gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    except Exception as e:
        print(f"Gemini sozlash xatosi: {e}")


CATEGORY = {
    "🎨 Logo": (
        "professional modern logo design, minimalist, vector style, flat design, "
        "clean composition, white background"
    ),
    "🖼 Realistik": (
        "ultra realistic photo, photorealistic, real camera photography, 8k resolution, "
        "highly detailed, natural lighting, realistic colors"
    ),
    "📱 Avatar": (
        "professional portrait avatar, profile picture, highly detailed face, studio lighting, "
        "sharp focus, realistic or semi-realistic style"
    ),
    "🏠 Interyer": (
        "professional interior design, photorealistic room render, modern furniture, "
        "cozy lighting, architectural digest style"
    ),
    "🌄 Landscape": (
        "epic landscape photography, breathtaking nature, realistic sky, natural lighting, "
        "National Geographic style, 8k"
    ),
    "🖥 UI/UX Web Dizayn": (
        "professional UI/UX web design, landing page, modern layout, clean interface, "
        "figma style, dribbble trending"
    ),
    "🏢 3D Arxitektura": (
        "highly detailed 3D architectural exterior render, modern building, realistic materials, "
        "octane render, cinematic lighting"
    ),
    "💎 Brending": (
        "complete brand identity mockup, corporate stationery set, business card design, "
        "elegant brand presentation"
    ),
    "🎮 Konsept Art": (
        "epic video game concept art, highly detailed environment, cinematic composition, "
        "artstation trending"
    ),
    "🏢 Reklama Banneri": (
        "professional advertising banner background, clean composition, marketing visual, "
        "large empty space for typography"
    )
}


NEGATIVE_PROMPT = (
    "wrong subject, unrelated object, random object, extra objects, distorted, deformed, "
    "bad anatomy, low quality, blurry, watermark, signature, text, letters, misspelled text, "
    "logo watermark, duplicate, noisy image, unrealistic artifacts"
)


# Oddiy fallback tarjimalar. Gemini ishlamay qolsa ham ba'zi o'zbekcha so'zlar to'g'ri ketadi.
UZ_EN_FALLBACK = {
    "quyosh": "the sun",
    "oy": "the moon",
    "yulduz": "star",
    "osmon": "sky",
    "tog": "mountain",
    "tog'": "mountain",
    "daryo": "river",
    "dengiz": "sea",
    "mashina": "car",
    "avtomobil": "car",
    "uy": "house",
    "daraxt": "tree",
    "gul": "flower",
    "it": "dog",
    "mushuk": "cat",
    "ot": "horse",
    "sher": "lion",
    "burgut": "eagle",
}


def fallback_translate(text: str) -> str:
    cleaned = text.strip().lower()
    return UZ_EN_FALLBACK.get(cleaned, text)


# --- GEMINI YORDAMIDA ANIQLASHTIRILGAN PROMPT YARATISH ---
async def process_prompt(user_text, category):
    base_style = CATEGORY.get(category, "")

    user_text = user_text.strip()

    if not user_text:
        return None, "Prompt bo'sh bo'lishi mumkin emas."

    # Agar Gemini API yo'q bo'lsa, oddiy fallback ishlaydi
    if not gemini_model:
        translated = fallback_translate(user_text)
        final_prompt = (
            f"{translated}, {base_style}, high quality, detailed image. "
            f"The image must show exactly this subject: {translated}. "
            f"No unrelated main objects."
        )
        return final_prompt, None

    system_prompt = f"""
You are a strict Uzbek-to-English AI image prompt converter.

USER REQUEST IN UZBEK:
"{user_text}"

IMAGE CATEGORY STYLE:
"{base_style}"

IMPORTANT RULES:
1. Preserve the user's main subject EXACTLY.
2. Do NOT replace the subject with another object.
3. Do NOT add unrelated objects.
4. If the user writes a short word like "quyosh", the final image prompt must be about the sun.
5. Translate the Uzbek request into accurate English.
6. Expand only with relevant visual details: lighting, camera, composition, realism, quality.
7. If category is realistic, make it photorealistic.
8. Do not include explanations.
9. Do not include quotation marks.
10. Return only one English prompt.

Final English prompt:
"""

    try:
        response = await asyncio.to_thread(
            gemini_model.generate_content,
            system_prompt,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.7,
                "max_output_tokens": 500
            }
        )

        final_prompt = response.text.strip()

        final_prompt = final_prompt.replace("```", "").replace("Prompt:", "").strip()

        if not final_prompt:
            translated = fallback_translate(user_text)
            final_prompt = f"{translated}, {base_style}, high quality, detailed image"

        # Asosiy obyektni saqlash uchun qo'shimcha qat'iy jumla
        final_prompt += (
            ". The image must accurately depict the user's requested subject. "
            "Do not change the main subject. No unrelated objects."
        )

        if category == "🏢 Reklama Banneri":
            final_prompt += (
                ", large empty spaces for typography, absolutely no text, "
                "no letters, no words, clean advertising composition"
            )

        # Log uchun. Render loglarida ko'rasiz.
        print("USER PROMPT:", user_text)
        print("FINAL PROMPT:", final_prompt)

        return final_prompt, None

    except Exception as e:
        print(f"Gemini Prompt xatosi: {e}")

        translated = fallback_translate(user_text)
        final_prompt = (
            f"{translated}, {base_style}, masterpiece, highly detailed, 8k. "
            f"The image must show exactly: {translated}. No unrelated objects."
        )

        return final_prompt, None


# --- STABILITY AI GA YUBORISH ---
async def generate_image(prompt, category):
    api_key = STABILITY_API_KEY.strip() if STABILITY_API_KEY else ""

    if not api_key:
        return None, "STABILITY_API_KEY topilmadi. config.py ichiga API key kiriting."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    final_prompt, prompt_error = await process_prompt(prompt, category)

    if prompt_error:
        return None, prompt_error

    # Dizayn toifasiga qarab rasm o'lchami
    aspect_ratio = "16:9"

    if category in ["🎨 Logo", "💎 Brending"]:
        aspect_ratio = "1:1"
    elif category in ["📱 Avatar"]:
        aspect_ratio = "9:16"
    elif category in ["🏠 Interyer", "🌄 Landscape", "🏢 3D Arxitektura", "🏢 Reklama Banneri"]:
        aspect_ratio = "16:9"
    elif category in ["🎮 Konsept Art"]:
        aspect_ratio = "16:9"

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
            files={
                "none": ("", b"")
            }
        )

    if r.status_code == 200:
        filename = f"temp_{uuid.uuid4().hex}.png"

        with open(filename, "wb") as f:
            f.write(r.content)

        return filename, None

    return None, f"{r.status_code}: {r.text}"
