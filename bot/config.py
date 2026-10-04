import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

# HMAC Secret key for anonymizing user Telegram ID (P-3 Rule)
HMAC_SECRET = os.getenv("HMAC_SECRET", "exiftool-secret-salt-key-2026")

# Max file size limit in MB (V-2 Rule: Max 20MB)
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "20"))
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# Max image dimension in pixels (V-4 Rule: Max 12,000 px per side)
MAX_IMAGE_DIMENSION = int(os.getenv("MAX_IMAGE_DIMENSION", "12000"))

# Network Timeout in seconds (K-3 Rule: 10s timeout)
NETWORK_TIMEOUT = int(os.getenv("NETWORK_TIMEOUT", "10"))

# Rate Limiting Settings (R-1, R-2, R-3 Rules)
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "100"))
MAX_CONCURRENT_PER_USER = int(os.getenv("MAX_CONCURRENT_PER_USER", "2"))
TEMPORARY_HOLD_MINUTES = int(os.getenv("TEMPORARY_HOLD_MINUTES", "15"))

# Geocoding settings (R-5 Rule)
ENABLE_REVERSE_GEOCODING = os.getenv("ENABLE_REVERSE_GEOCODING", "true").lower() == "true"
NOMINATIM_USER_AGENT = os.getenv("NOMINATIM_USER_AGENT", "TelegramExifBot/1.0 (Contact: admin@exifbot.org)")
