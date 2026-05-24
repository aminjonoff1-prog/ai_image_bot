import asyncio
import time
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import google.generativeai as genai

from config import GEMINI_API_KEY

# Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


async def generate_coursework(topic, user_id):

    prompt = f"""
You are a professional university academic writer.

Write a COMPLETE university-level coursework in Uzbek language.

TOPIC:
{topic}

STRICT REQUIREMENTS:
- Academic Uzbek language
- Professional structure
- Minimum 15 pages worth of text
- Include:
    1. Title
    2. Mundarija
    3. Kirish
    4. Main chapters
    5. Analysis
    6. Conclusion
    7. References

- Use realistic academic style
- Add numbered sections
- Add bullet points where needed
- Make it detailed and professional
- University standard
- No markdown

Generate full coursework.
"""

    response = await asyncio.to_thread(
        model.generate_content,
        prompt
    )

    text = response.text

    # DOCX yaratish
    doc = Document()

    # FONT
    style = doc.styles['Normal']
    style.font.name = 'Times New Roman'
    style.font.size = Pt(14)

    # TITLE
    title = doc.add_paragraph()
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    run = title.add_run(topic.upper())
    run.bold = True
    run.font.size = Pt(20)

    doc.add_paragraph("\n")

    # CONTENT
    paragraphs = text.split("\n")

    for line in paragraphs:

        line = line.strip()

        if not line:
            continue

        # Heading
        if (
            "KIRISH" in line.upper()
            or "XULOSA" in line.upper()
            or "MUNDARIJA" in line.upper()
            or "FOYDALANILGAN" in line.upper()
        ):
            p = doc.add_paragraph()
            r = p.add_run(line)
            r.bold = True
            r.font.size = Pt(16)
            continue

        p = doc.add_paragraph(line)
        p.paragraph_format.space_after = Pt(8)

    filename = f"coursework_{user_id}_{int(time.time())}.docx"

    doc.save(filename)

    return filename
