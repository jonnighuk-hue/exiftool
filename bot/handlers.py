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
    """Mengunduh file dari telegram ke RAM (BytesIO) dengan validasi ukuran."""
    if message.document:
        if (
            message.document.file_size
            and message.document.file_size > MAX_FILE_SIZE_BYTES
        ):
            return None, f"Ukuran file melebihi batas {MAX_FILE_SIZE_MB}MB."
        tg_file = await message.document.get_file()
        file_name = getattr(message.document, "file_name", "image.jpg")
    elif message.photo:
        tg_file = await message.photo[-1].get_file()
        file_name = "photo.jpg"
    else:
        return None, "File tidak valid."

    data = bytes(await tg_file.download_as_bytearray())
    return data, file_name


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /start dan /help."""
    text = (
        "👋 *Selamat Datang di Bot EXIF Inspector & Cleaner!*\n\n"
        "🔒 *Jaminan Privasi*: Foto Anda hanya diproses di RAM dan **tidak pernah disimpan** ke disk atau server.\n\n"
        "💡 *Cara Pakai*:\n"
        "Kirim foto Anda sebagai **File/Dokumen** (bukan foto biasa) "
        "agar Telegram tidak menghapus metadata EXIF secara otomatis.\n\n"
        "✨ *Fitur Bot*:\n"
        "• 📋 Baca metadata EXIF (Kamera, ISO, Aperture, Waktu, dll.)\n"
        "• 🤖 Deteksi jejak metadata AI (Midjourney, Stable Diffusion, DALL-E, dll.)\n"
        "• 📍 Tampilkan titik lokasi GPS di peta & alamat wilayah\n"
        "• 🧹 Hapus EXIF & unduh gambar bersih tanpa merubah orientasi foto"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def image_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler ketika pengguna mengunggah foto atau dokumen gambar."""
    msg = update.message
    user_id = update.effective_user.id
    is_photo = bool(msg.photo)

    # 1. Rate Limiter check
    allowed, wait_sec = rate_limiter.is_allowed(user_id)
    if not allowed:
        await msg.reply_text(
            f"⏱️ Batas penggunaan tercapai. Silakan tunggu {wait_sec} detik sebelum mengirim file lagi."
        )
        return

    # 2. Download File ke RAM
    data, error_msg = await download_file(msg)
    if not data:
        await msg.reply_text(f"❌ {error_msg}")
        return

    # 3. Read EXIF
    try:
        info, gps = read_exif(data)
    except Exception as e:
        logger.error(f"Gagal membaca file gambar: {e}")
        await msg.reply_text("❌ Gagal membaca gambar. Pastikan formatnya valid (JPG/PNG/HEIC).")
        return

    if not info and not gps:
        warning_text = "ℹ️ Tidak ditemukan data EXIF pada gambar ini."
        if is_photo:
            warning_text += (
                "\n\n⚠️ *Penyebab*: Anda mengirimkan sebagai Foto biasa sehingga Telegram otomatis menghapus metadata EXIF-nya.\n"
                "📌 *Solusi*: Kirim ulang sebagai **File/Dokumen**."
            )
        await msg.reply_text(warning_text, parse_mode="Markdown" if is_photo else None)
        return

    # 4. Deteksi Metadata AI & Kamera
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

    # Mode ringkas sebagai default
    exif_body = format_exif_text(info, full_mode=False)

    buttons = []
    coords = gps_to_decimal(gps)
    if coords:
        buttons.append(InlineKeyboardButton("📍 Lokasi GPS", callback_data="gps"))
        buttons.append(InlineKeyboardButton("🗺️ Alamat", callback_data="address"))

    buttons.append(InlineKeyboardButton("📄 Mode Lengkap", callback_data="toggle_full"))
    buttons.append(InlineKeyboardButton("🧹 Hapus EXIF", callback_data="clean"))

    # Susun tombol menjadi urutan inline keyboard yang rapi
    keyboard = []
    row1 = [b for b in buttons if b.callback_data in ("gps", "address")]
    if row1:
        keyboard.append(row1)
    keyboard.append([b for b in buttons if b.callback_data in ("toggle_full", "clean")])

    await msg.reply_text(
        f"📋 *Ringkasan EXIF:*\n\n{header_text}{exif_body}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard),
        reply_to_message_id=msg.message_id,
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk aksi callback tombol inline."""
    query = update.callback_query
    await query.answer()
    original = query.message.reply_to_message

    if not original:
        await query.message.reply_text("Pesan file asli tidak ditemukan. Silakan kirim ulang gambarnya.")
        return

    data, _ = await download_file(original)
    if not data:
        await query.message.reply_text("Gagal mengunduh file asli.")
        return

    info, gps = read_exif(data)
    coords = gps_to_decimal(gps)

    if query.data == "gps":
        if coords:
            await query.message.reply_location(latitude=coords[0], longitude=coords[1])
            await query.message.reply_text(
                f"📍 *Koordinat GPS:* `{coords[0]:.6f}, {coords[1]:.6f}`",
                parse_mode="Markdown",
            )
        else:
            await query.message.reply_text("Tidak ada data GPS yang valid.")

    elif query.data == "address":
        if coords:
            address = reverse_geocode(coords[0], coords[1])
            if address:
                await query.message.reply_text(
                    f"🗺️ *Estimasi Alamat:* \n`{address}`\n\n📍 Koordinat: `{coords[0]:.6f}, {coords[1]:.6f}`",
                    parse_mode="Markdown",
                )
            else:
                await query.message.reply_text(f"📍 Koordinat: `{coords[0]:.6f}, {coords[1]:.6f}` (Nama alamat tidak ditemukan)")
        else:
            await query.message.reply_text("Tidak ada data GPS.")

    elif query.data == "toggle_full":
        full_text = format_exif_text(info, full_mode=True)
        keyboard = [
            [InlineKeyboardButton("📋 Ringkas", callback_data="toggle_compact"), InlineKeyboardButton("🧹 Hapus EXIF", callback_data="clean")]
        ]
        if coords:
            keyboard.insert(0, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="gps"), InlineKeyboardButton("🗺️ Alamat", callback_data="address")])

        await query.message.edit_text(
            f"📄 *Data EXIF Lengkap:*\n\n{full_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "toggle_compact":
        compact_text = format_exif_text(info, full_mode=False)
        keyboard = [
            [InlineKeyboardButton("📄 Mode Lengkap", callback_data="toggle_full"), InlineKeyboardButton("🧹 Hapus EXIF", callback_data="clean")]
        ]
        if coords:
            keyboard.insert(0, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="gps"), InlineKeyboardButton("🗺️ Alamat", callback_data="address")])

        await query.message.edit_text(
            f"📋 *Ringkasan EXIF:*\n\n{compact_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "clean":
        try:
            cleaned_data, ext = strip_exif(data)
            orig_filename = getattr(original.document, "file_name", "image.jpg") if original.document else "image.jpg"
            base_name = os.path.splitext(orig_filename)[0]
            out_filename = f"clean_{base_name}.{ext}"

            await query.message.reply_document(
                document=io.BytesIO(cleaned_data),
                filename=out_filename,
                caption="✅ Metadata EXIF telah berhasil dihapus secara permanen.",
            )
        except Exception as e:
            logger.error(f"Gagal menghapus EXIF: {e}")
            await query.message.reply_text("❌ Gagal menghapus metadata EXIF.")
