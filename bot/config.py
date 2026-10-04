import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# Max file size limit in MB (Telegram Bot API limit is 20MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Rate Limiting: Max requests per user within WINDOW_SECONDS
RATE_LIMIT_CALLS = int(os.getenv("RATE_LIMIT_CALLS", "10"))
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW", "60"))

# Geocoding settings
ENABLE_REVERSE_GEOCODING = os.getenv("ENABLE_REVERSE_GEOCODING", "true").lower() == "true"
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "TelegramExifBot/1.0")
