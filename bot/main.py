import logging
import sys
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from bot.config import BOT_TOKEN
from bot.handlers import (
    button_handler,
    image_handler,
    start_handler,
)

# Configuration logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    """Menginisialisasi dan menjalankan Telegram Bot."""
    if not BOT_TOKEN:
        logger.error(
            "BOT_TOKEN tidak ditemukan! Pastikan BOT_TOKEN telah diisi di file"
            " .env"
        )
        print("[!] ERROR: BOT_TOKEN tidak ditemukan di file .env")
        print("Silakan buat file .env dan isi BOT_TOKEN=token_bot_anda (dapatkan dari @BotFather)")
        sys.exit(1)

    # Inisialisasi Application telegram
    app = Application.builder().token(BOT_TOKEN).build()

    # Registrasi handlers
    app.add_handler(CommandHandler(["start", "help"], start_handler))
    app.add_handler(
        MessageHandler(filters.PHOTO | filters.Document.IMAGE, image_handler)
    )
    app.add_handler(CallbackQueryHandler(button_handler))

    logger.info("🤖 Bot EXIF Cleaner & Inspector siap berjalan...")
    app.run_polling()


if __name__ == "__main__":
    main()
