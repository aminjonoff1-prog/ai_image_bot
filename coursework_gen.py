import asyncio
import time
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import google.generativeai as genai

try:
    from config import GEMINI_API_KEY
except ImportError:
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

gemini_model = None

if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY.strip())
    except Exception as e:
        print(f"Gemini configure xatosi: {e}")


def get_working_model():
    model_names = [
        "gemini-2.0-flash",
        "gemini-2.0-flash-exp",
        "gemini-1.5-pro",
        "gemini-pro"
    ]

    for model_name in model_names:
        try:
            model = genai.GenerativeModel(model_name)
            # test request
            response = model.generate_content("Salom")
            if response:
                print(f"Ishlayotgan Gemini modeli: {model_name}")
                return model
        except Exception as e:
            print(f"Model ishlamadi: {model_name} -> {e}")

    return None


gemini_model = get_working_model()


async def generate_coursework(topic: str, user_id: int) -> str:
    """Akademik kurs ishini DOCX formatida yaratadi"""

    if not gemini_model:
        raise ValueError("Ishlaydigan Gemini modeli topilmadi.")

    prompt = f"""
Siz tajribali universitet professori va akademik yozuvchisiz.

Quyidagi mavzuda o'zbek tilida mukammal kurs ishi yozing:

MAVZU: {topic}

QAT'IY TALABLAR:
- O'zbek tilida yozing
- Akademik uslubda yozing
- Juda batafsil yozing
- Quyidagi bo'limlar bo'lsin:
1. MUNDARIJA
2. KIRISH
3. I-BO'LIM
4. 1.1
5. 1.2
6. II-BO'LIM
7. 2.1
8. 2.2
9. XULOSA
10. FOYDALANILGAN ADABIYOTLAR

- Matn toza bo'lsin
- Hech qanday markdown ishlatmang
- Har bir bo'limni batafsil yoritib bering
"""

    try:
        response = await asyncio.to_thread(gemini_model.generate_content, prompt)
        full_text = response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini matn generatsiyasida xatolik: {e}")

    doc = Document()

    # Marginlar
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(1.18)
        section.right_margin = Inches(0.59)

    # Font
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)

    # Title page
    p1 = doc.add_paragraph()
    p1.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r1 = p1.add_run("O'ZBEKISTON RESPUBLIKASI OLIY TA'LIM, FAN VA INNOVATSIYALAR VAZIRLIGI\n\n")
    r1.bold = True
    r1.font.size = Pt(12)

    p2 = doc.add_paragraph()
    p2.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r2 = p2.add_run("KURS ISHI\n\n")
    r2.bold = True
    r2.font.size = Pt(20)
    r2.font.color.rgb = RGBColor(11, 29, 58)

    p3 = doc.add_paragraph()
    p3.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r3 = p3.add_run(f"MAVZU: {topic.upper()}\n\n\n")
    r3.bold = True
    r3.font.size = Pt(16)

    p4 = doc.add_paragraph()
    p4.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    r4 = p4.add_run("Bajardi: __________________\nIlmiy rahbar: __________________\n\n\n")
    r4.font.size = Pt(12)

    p5 = doc.add_paragraph()
    p5.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    r5 = p5.add_run("TOSHKENT - 2024")
    r5.bold = True
    r5.font.size = Pt(12)

    doc.add_page_break()

    lines = full_text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.15
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_PARAGRAPH_ALIGNMENT.JUSTIFY

        upper_line = line.upper()

        if (
            "MUNDARIJA" in upper_line
            or "KIRISH" in upper_line
            or "XULOSA" in upper_line
            or "FOYDALANILGAN ADABIYOTLAR" in upper_line
            or "I-BO'LIM" in upper_line
            or "II-BO'LIM" in upper_line
            or line.startswith("1.1")
            or line.startswith("1.2")
            or line.startswith("2.1")
            or line.startswith("2.2")
        ):
            p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
            run = p.add_run(line)
            run.bold = True
            run.font.size = Pt(15)
        else:
            p.paragraph_format.first_line_indent = Inches(0.49)
            p.add_run(line)

    filename = f"coursework_{user_id}_{int(time.time())}.docx"
    doc.save(filename)
    return filename
