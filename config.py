import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
FREE_LIMIT = int(os.getenv("FREE_LIMIT", 5))

print("Kofiglar xavfsiz yuklandi OK")
