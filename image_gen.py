import httpx
import asyncio
import uuid
import google.generativeai as genai
from config import STABILITY_API_KEY, GEMINI_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
        gemini_model = genai.GenerativeModel("gemini-pro")
    except Exception as e:
        print(f"Gemini sozlash xatosi: {e}")


CATEGORY = {
    "🎨 Logo": "professional modern minimalist logo, vector, clean design, branding, white background",
    "🖼 Realistik": "ultra realistic photo, photorealistic, natural lighting, highly detailed, realistic colors",
    "📱 Avatar": "professional portrait avatar, profile picture, detailed face, studio lighting",
    "🏠 Interyer": "professional interior design, photorealistic room render, modern furniture",
    "🌄 Landscape": "epic realistic landscape photography, nature, cinematic sky, detailed environment",
    "🖥 UI/UX Web Dizayn": "professional UI/UX web design, landing page, modern interface, figma style",
    "🏢 3D Arxitektura": "highly detailed 3D architecture render, modern exterior, realistic materials",
    "💎 Brending": "brand identity mockup, elegant branding, premium business design",
    "🎮 Konsept Art": "epic concept art, cinematic composition, highly detailed environment",
    "🏢 Reklama Banneri": "professional advertising banner background, clean composition, large empty text area"
}

NEGATIVE_PROMPT = (
    "wrong subject, unrelated object, random object, extra objects, distorted, deformed, "
    "low quality, blurry, watermark, signature, text, letters, misspelled text, duplicate"
)

UZ_EN_FALLBACK = {
    "quyosh": "the sun in the sky",
    "oy": "the moon in the night sky",
    "yulduz": "a bright star",
    "osmon": "clear blue sky",
    "tog": "mountain",
    "tog'": "mountain",
    "daryo": "river",
    "dengiz": "sea",
    "mashina": "modern car",
    "uy": "modern house",
    "daraxt": "green tree",
    "gul": "beautiful flower",
    "it": "dog",
    "mushuk": "cat",
    "ot": "horse",
    "sher": "lion",
    "burgut": "eagle"
}


def fallback_translate(text: str) -> str:
    cleaned = text.strip().lower()
    return UZ_EN_FALLBACK.get(cleaned, text)


async def process_prompt(user_text, category):
    base_style = CATEGORY.get(category, "")
    user_text = user_text.strip()

    if not user_text:
        return None, "Prompt bo'sh bo'lmasligi kerak."

    # Juda qisqa promptlar uchun fallback
    translated = fallback_translate(user_text)

    if not gemini_model:
        final_prompt = (
            f"{translated}, {base_style}. "
            f"The image must show exactly this subject: {translated}. "
            f"No unrelated objects."
        )
        return final_prompt, None

    system_prompt = f"""
You are a strict Uzbek-to-English AI image prompt converter.

USER REQUEST:
{user_text}

CATEGORY STYLE:
{base_style}

STRICT RULES:
1. Preserve the user's main subject exactly.
2. Do not replace the object with another object.
3. If user says 'quyosh', it must mean the sun in the sky.
4. Translate Uzbek into accurate English.
5. Add only relevant visual details.
6. No unrelated objects.
7. Return only one final English image prompt.

Final prompt:
"""

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, system_prompt)
        final_prompt = response.text.strip()

        if not final_prompt:
            final_prompt = translated

        final_prompt += (
            f". The image must clearly depict: {translated}. "
            f"Do not change the main subject. No unrelated objects."
        )

        if category == "🏢 Reklama Banneri":
            final_prompt += ", large empty space for text, no letters, no typography"

        print("USER:", user_text)
        print("FINAL:", final_prompt)

        return final_prompt, None

    except Exception as e:
        print(f"Prompt xatosi: {e}")
        final_prompt = (
            f"{translated}, {base_style}. "
            f"The image must show exactly: {translated}. No unrelated objects."
        )
        return final_prompt, None


async def generate_image(prompt, category):
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

    return None, f"{r.status_code}: {r.text}"
