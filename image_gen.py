import httpx
import asyncio
import google.generativeai as genai
from config import STABILITY_API_KEY, GEMINI_API_KEY

URL = "https://api.stability.ai/v2beta/stable-image/generate/ultra"

# --- GEMINI SOZLAMALARI ---
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY.strip())
    gemini_model = genai.GenerativeModel('gemini-1.5-pro-latest')

# Barcha toifalar uchun bazaviy uslublar (Gemini buni yanada boyitadi)
CATEGORY = {
    "🎨 Logo": "professional modern logo design, minimalist, vector, flat design, white background",
    "🖼 Realistik": "ultra realistic photo, 8k resolution, highly detailed, cinematic lighting, photorealistic",
    "📱 Avatar": "portrait, profile picture, highly detailed face, studio lighting, 8k",
    "🏠 Interyer": "professional interior design, architectural digest, photorealistic, Unreal Engine 5 render, cozy lighting",
    "🌄 Landscape": "epic landscape photography, breathtaking nature, National Geographic style, 8k",
    "🖥 UI/UX Web Dizayn": "professional UI/UX web design, landing page, modern layout, clean interface, dribbble trending, figma style",
    "🏢 3D Arxitektura": "highly detailed 3D architectural exterior render, Zaha Hadid style, modern building, octane render",
    "💎 Brending": "complete brand identity mockup, corporate stationery set, business card design, elegant setup",
    "🎮 Konsept Art": "epic video game concept art, highly detailed environment, artstation trending",
    "🏢 Reklama Banneri": "professional advertising banner background, outdoor signage mockup, extremely high detail"
}

# --- GEMINI YORDAMIDA PROMPT YARATISH ---
async def process_prompt(user_text, category):
    if not GEMINI_API_KEY:
        return user_text + ", high quality, 8k resolution"

    base_style = CATEGORY.get(category, "")
    
    system_prompt = (f"Sen professional dizayner va Prompt Engineersan. "
                     f"Dizayn toifasi va uslubi: '{base_style}'. "
                     f"Mijozning so'rovi: '{user_text}'. "
                     f"Shu ma'lumotlardan foydalanib, Stability AI (Ultra) modeli uchun "
                     f"mukammal, detallarga boy, fotografik yorug'lik, kompozitsiya va kerakli "
                     f"render uslublari qo'shilgan INGLIZ tilidagi prompt yozib ber. "
                     f"Faqat inglizcha promptni o'zini qaytar, hech qanday izoh qo'shma.")
    
    try:
        response = await asyncio.to_thread(gemini_model.generate_content, system_prompt)
        final_prompt = response.text.strip()
        
        # Banner fonida AI matn yozib xato qilmasligi uchun xavfsizlik qatlami
        if category == "🏢 Reklama Banneri":
            final_prompt += ", large empty spaces for typography, absolutely no text, clean composition"
            
        return final_prompt
    except Exception as e:
        print(f"Gemini Prompt xatosi: {e}")
        return user_text + ", masterpiece, highly detailed, 8k"

# --- STABILITY AI GA YUBORISH ---
async def generate_image(prompt, category):
    api_key = STABILITY_API_KEY.strip() if STABILITY_API_KEY else ""
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "image/*"
    }

    # Gemini orqali mukammal promptni shakllantirish
    final_prompt = await process_prompt(prompt, category)

    # Dizayn toifasiga qarab rasm o'lchamini (aspect ratio) moslashtirish
    aspect_ratio = "16:9" 
    if category in ["🎨 Logo", "💎 Brending"]:
        aspect_ratio = "1:1"
    elif category in ["📱 Avatar", "🏠 Interyer", "🎮 Konsept Art"]:
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
