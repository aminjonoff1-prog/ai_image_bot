import httpx
import asyncio
from deep_translator import GoogleTranslator
from config import STABILITY_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

CATEGORY = {
    # Eski toifalar ... (Logo, Realistik va hk.)
    
    # YANGI: Murakkab tashqi reklama banneri foni
    "🏢 Reklama Banneri": "professional advertising banner background, outdoor signage mockup, extremely high detail, cinematic lighting, corporate style, volumetric lighting, photorealistic. WARNING: This will generate ONLY the background imagery, not readable text."
}

async def process_prompt(text, category):
    try:
        translated = await asyncio.to_thread(
            GoogleTranslator(source='auto', target='en').translate,
            text
        )
        
        # Banner uchun maxsus ko'rsatmalar
        if category == "🏢 Reklama Banneri":
            # Biz AIdan matn yozmaslikni iltimos qilamiz, chunki u xato yozadi.
            # O'rniga, matn uchun bo'sh joy qoldirishni so'raymiz.
            return f"masterpiece, detailed imagery of {translated}, large empty spaces for typography, no text, clean composition, 8k resolution"
        
        return translated + ", masterpiece, highly detailed, 8k resolution"
    except:
        return text

async def generate_image(prompt, category):
    api_key = STABILITY_API_KEY.strip() if STABILITY_API_KEY else ""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    base = CATEGORY.get(category, "")
    # Promtni qayta ishlashga toifani ham yuboramiz
    final_prompt = await process_prompt(prompt, category)

    # O'lchamni tanlash (Bannerlar uchun odatda yotiq 16:9 yoki tik 9:16)
    # Foydalanuvchi 100x70 degani yotiq benerni anglatadi (tasavvurda).
    aspect_ratio = "16:9" 
    if category == "🎨 Logo":
        aspect_ratio = "1:1"
    elif category == "📱 Avatar":
        aspect_ratio = "9:16"

    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(
            URL,
            headers=headers,
            data={
                "prompt": final_prompt,
                "output_format": "png",
                "aspect_ratio": aspect_ratio
            },
            files={"none": (None, "")}
        )

        if r.status_code == 200:
            filename = f"temp_{hash(prompt)}.png"
            with open(filename, "wb") as f:
                f.write(r.content)
            return filename, None

        return None, f"{r.status_code}: {r.text}"
