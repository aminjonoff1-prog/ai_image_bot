import httpx
import asyncio
from deep_translator import GoogleTranslator
from config import STABILITY_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

CATEGORY = {
    "🎨 Logo": "modern logo design, minimalist, vector",
    "🖼 Realistik": "ultra realistic photo",
    "📱 Avatar": "portrait, profile picture",
    "🏠 Interyer": "interior design, modern house",
    "🌄 Landscape": "beautiful landscape, nature"
}

async def process_prompt(text):
    try:
        translated = await asyncio.to_thread(
            GoogleTranslator(source='auto', target='en').translate,
            text
        )
        return translated + ", highly detailed, cinematic lighting, 8k"
    except:
        return text

async def generate_image(prompt, category):
    # Config'dan olingan kalitdagi ortiqcha bo'sh joylarni tozalaymiz
    api_key = STABILITY_API_KEY.strip() if STABILITY_API_KEY else ""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    base = CATEGORY.get(category, "")
    final_prompt = await process_prompt(base + ", " + prompt)

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            URL,
            headers=headers,
            data={
                "prompt": final_prompt,
                "output_format": "png"
            },
            files={"none": (None, "")}
        )

        if r.status_code == 200:
            filename = f"temp_{hash(prompt)}.png"
            with open(filename, "wb") as f:
                f.write(r.content)
            return filename, None

        return None, f"{r.status_code}: {r.text}"
