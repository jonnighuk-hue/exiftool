import io
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from bot.config import MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB
from bot.exif_service import (
    detect_ai_signature,
    format_exif_text,
    gps_to_decimal,
    read_exif,
    strip_exif,
)
from bot.geo_service import reverse_geocode
from bot.ratelimit import rate_limiter

logger = logging.getLogger(__name__)


async def download_file(message) -> tuple[bytes | None, str | None]:
    """Mengunduh file dari telegram ke RAM (BytesIO) dengan validasi ukuran V-2."""
    if message.document:
        if (
            message.document.file_size
            and message.document.file_size > MAX_FILE_SIZE_BYTES
        ):
            return None, f"File melebihi {MAX_FILE_SIZE_MB} MB. Kompres atau kirim file yang lebih kecil."
        tg_file = await message.document.get_file()
        file_name = getattr(message.document, "file_name", "image.jpg")
    elif message.photo:
        tg_file = await message.photo[-1].get_file()
        file_name = "photo.jpg"
    else:
        return None, "Format file tidak didukung."

    data = bytes(await tg_file.download_as_bytearray())
    return data, file_name


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /start dan /help."""
    user_id = update.effective_user.id
    if rate_limiter.is_blocked(user_id):  # Aturan R-4
        return

    text = (
        "👋 *Selamat Datang di Bot EXIF Inspector & Cleaner!*\n\n"
        "🔒 *Jaminan Privasi*: Foto Anda hanya diproses di RAM dan **tidak pernah disimpan** ke disk atau server.\n\n"
        "💡 *Cara Pakai*:\n"
        "Kirim foto sebagai **File/Dokumen** (bukan foto biasa) "
        "agar Telegram tidak menghapus metadata EXIF secara otomatis.\n\n"
        "✨ *Fitur & Perintah Bot*:\n"
        "• 📋 Baca metadata EXIF & Deteksi AI\n"
        "• 📍 Tampilkan lokasi GPS di peta & alamat wilayah\n"
        "• 🧹 Hapus EXIF & unduh gambar bersih\n"
        "• `/hapus_data` - Hapus seluruh data pengguna & riwayat Anda"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def hapus_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /hapus_data (Aturan P-6)."""
    user_id = update.effective_user.id
    if rate_limiter.is_blocked(user_id):  # Aturan R-4
        return

    # Reset rate limit & user state
    if user_id in rate_limiter.user_minute_history:
        del rate_limiter.user_minute_history[user_id]
    if user_id in rate_limiter.user_day_history:
        del rate_limiter.user_day_history[user_id]
    if user_id in rate_limiter.user_violations:
        del rate_limiter.user_violations[user_id]

    await update.message.reply_text(
        "✅ Seluruh riwayat dan data pengguna Anda telah dihapus secara permanen dari memori sistem.",
        parse_mode="Markdown"
    )


async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler ketika pengguna mengunggah foto atau dokumen gambar."""
    msg = update.message
    user_id = update.effective_user.id
    is_photo = bool(msg.photo)

    # Aturan R-4: Abaikan pengguna yang terblokir
    if rate_limiter.is_blocked(user_id):
        return

    # Aturan R-1 & R-3: Rate Limiting
    allowed, wait_sec = rate_limiter.is_allowed(user_id)
    if not allowed:
        await msg.reply_text(
            f"Terlalu cepat. Coba lagi dalam {wait_sec} detik."
        )
        return

    # Aturan R-2: Maksimal 2 pemrosesan bersamaan
    if not rate_limiter.acquire_concurrent(user_id):
        await msg.reply_text("Terlalu banyak pemrosesan bersamaan. Harap tunggu hingga selesai.")
        return

    try:
        # Download file ke RAM (P-1 Rule)
        data, error_msg = await download_file(msg)
        if not data:
            await msg.reply_text(f"⚠️ {error_msg}")
            return

        # Read EXIF
        try:
            info, gps = read_exif(data)
        except ValueError as ve:
            # Peringatan batas dimensi V-4
            await msg.reply_text(f"⚠️ {ve}")
            return
        except Exception as e:
            logger.error(f"Gagal membaca file gambar: {e}")
            await msg.reply_text("Format ini belum didukung. Coba JPG, PNG, TIFF, WebP, atau HEIC.")
            return

        if not info and not gps:
            warning_text = "Tidak ada EXIF."
            if is_photo:
                warning_text += (
                    " Telegram biasanya menghapusnya. Kirim ulang sebagai **File/Dokumen**."
                )
            await msg.reply_text(warning_text, parse_mode="Markdown" if is_photo else None)
            return

        # Deteksi Metadata AI & Perangkat
        ai_source = detect_ai_signature(info)
        make = info.get("Make", "")
        model = info.get("Model", "")
        device_str = f"{make} {model}".strip()

        header_lines = []
        if ai_source:
            header_lines.append(f"🤖 *Deteksi AI*: `Terdeteksi jejak {ai_source}`")
        if device_str:
            header_lines.append(f"📸 *Perangkat*: `{device_str}`")

        header_text = ("\n".join(header_lines) + "\n\n") if header_lines else ""

        # Default: Summary Mode
        exif_body = format_exif_text(info, full_mode=False)

        buttons = []
        coords = gps_to_decimal(gps)
        if coords:
            buttons.append(InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps"))

        buttons.append(InlineKeyboardButton("📄 Semua tag", callback_data="act:full"))
        buttons.append(InlineKeyboardButton("🧹 Hapus EXIF", callback_data="act:clean"))

        keyboard = []
        row1 = [b for b in buttons if b.callback_data == "act:gps"]
        if row1:
            keyboard.append(row1)
        keyboard.append([b for b in buttons if b.callback_data in ("act:full", "act:clean")])

        await msg.reply_text(
            f"📋 *Ringkasan EXIF:*\n\n{header_text}{exif_body}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
            reply_to_message_id=msg.message_id,
        )
    finally:
        # Lepaskan slot pemrosesan bersamaan (R-2)
        rate_limiter.release_concurrent(user_id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk callback tombol inline (3.3 Callback Schema)."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if rate_limiter.is_blocked(user_id):
        return

    original = query.message.reply_to_message
    if not original:
        await query.message.reply_text("Pesan asal tidak ditemukan. Kirim ulang filenya, ya.")
        return

    data, _ = await download_file(original)
    if not data:
        await query.message.reply_text("Gagal mengunduh file asal.")
        return

    info, gps = read_exif(data)
    coords = gps_to_decimal(gps)

    # 3.3 Callback Schema
    if query.data == "act:gps":
        if coords:
            await query.message.reply_location(latitude=coords[0], longitude=coords[1])
            address = reverse_geocode(coords[0], coords[1])
            addr_text = f"\n🗺️ *Alamat:* `{address}`" if address else ""
            await query.message.reply_text(
                f"📍 *Koordinat GPS:* `{coords[0]:.6f}, {coords[1]:.6f}`{addr_text}",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text("Tidak ada data GPS yang valid.")

    elif query.data == "act:full":
        full_text = format_exif_text(info, full_mode=True)
        keyboard = [
            [InlineKeyboardButton("📋 Ringkasan", callback_data="act:summary"), InlineKeyboardButton("🧹 Hapus EXIF", callback_data="act:clean")]
        ]
        if coords:
            keyboard.insert(0, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps")])

        await query.message.edit_text(
            f"📄 *Data EXIF Lengkap:*\n\n{full_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "act:summary":
        compact_text = format_exif_text(info, full_mode=False)
        keyboard = [
            [InlineKeyboardButton("📄 Semua tag", callback_data="act:full"), InlineKeyboardButton("🧹 Hapus EXIF", callback_data="act:clean")]
        ]
        if coords:
            keyboard.insert(0, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps")])

        await query.message.edit_text(
            f"📋 *Ringkasan EXIF:*\n\n{compact_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "act:clean":
        try:
            cleaned_data, ext = strip_exif(data)
            orig_filename = getattr(original.document, "file_name", "image.jpg") if original.document else "image.jpg"
            base_name = os.path.splitext(orig_filename)[0]
            out_filename = f"clean_{base_name}.{ext}"

            await query.message.reply_document(
                document=io.BytesIO(cleaned_data),
                filename=out_filename,
                caption="✅ Metadata EXIF sudah dihapus.",
            )
        except Exception as e:
            logger.error(f"Gagal menghapus EXIF: {e}")
            await query.message.reply_text("Gagal menghapus metadata EXIF.")
