import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_ID = int(os.getenv("ADMIN_ID", 7168047390))
BOT_TOKEN = os.getenv("BOT_TOKEN")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
FREE_LIMIT = int(os.getenv("FREE_LIMIT", 5))

print("Kofiglar xavfsiz yuklandi OK")
