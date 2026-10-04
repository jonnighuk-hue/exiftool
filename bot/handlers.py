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
    read_multi_group_metadata,
    strip_exif_lossless,
    strip_exif_lossy,
)
from bot.geo_service import reverse_geocode
from bot.ratelimit import rate_limiter
from benchmark.metrics import calculate_psnr, calculate_ssim

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
    if rate_limiter.is_blocked(user_id):
        return

    text = (
        "👋 *Selamat Datang di Bot EXIF Inspector & Research Tool (Scopus Q1 Project)*\n\n"
        "🔒 *Jaminan Privasi*: Foto diproses murni di RAM dan **tidak pernah disimpan**.\n\n"
        "✨ *Fitur Riset Terintegrasi*:\n"
        "• 🔬 **Riset A**: Metadata Survival (EXIF, GPS, XMP, ICC, C2PA, MakerNote)\n"
        "• 🧹 **Riset B**: Analisis Residual Leakage (Lossless vs Lossy Stripping)\n"
        "• 🤖 **Riset C**: Forensik AI & Deteksi Ketidakcocokan Logika Metadata\n\n"
        "💡 *Cara Pakai*:\n"
        "Kirim foto sebagai **File/Dokumen** (bukan foto biasa) "
        "agar Telegram tidak menghapus metadata EXIF secara otomatis."
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def hapus_data_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk perintah /hapus_data (Aturan P-6)."""
    user_id = update.effective_user.id
    if rate_limiter.is_blocked(user_id):
        return

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

    if rate_limiter.is_blocked(user_id):
        return

    allowed, wait_sec = rate_limiter.is_allowed(user_id)
    if not allowed:
        await msg.reply_text(f"Terlalu cepat. Coba lagi dalam {wait_sec} detik.")
        return

    if not rate_limiter.acquire_concurrent(user_id):
        await msg.reply_text("Terlalu banyak pemrosesan bersamaan. Harap tunggu hingga selesai.")
        return

    try:
        data, error_msg = await download_file(msg)
        if not data:
            await msg.reply_text(f"⚠️ {error_msg}")
            return

        try:
            multi_meta = read_multi_group_metadata(data)
            info = multi_meta["raw_info"]
            gps = multi_meta["raw_gps"]
        except ValueError as ve:
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

        ai_source = multi_meta["ai_signature"]
        make = info.get("Make", "")
        model = info.get("Model", "")
        device_str = f"{make} {model}".strip()

        header_lines = []
        if ai_source:
            header_lines.append(f"🤖 *Deteksi AI*: `Terdeteksi jejak {ai_source}`")
        if device_str:
            header_lines.append(f"📸 *Perangkat*: `{device_str}`")

        header_text = ("\n".join(header_lines) + "\n\n") if header_lines else ""
        exif_body = format_exif_text(info, full_mode=False)

        buttons = [
            [InlineKeyboardButton("🔬 Laporan Riset A+B+C", callback_data="act:research")],
        ]

        coords = gps_to_decimal(gps)
        if coords:
            buttons.append([InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps")])

        buttons.append([
            InlineKeyboardButton("📄 Semua tag", callback_data="act:full"),
            InlineKeyboardButton("🧹 Hapus (Lossless)", callback_data="act:clean_lossless"),
            InlineKeyboardButton("🎨 Hapus (Lossy)", callback_data="act:clean_lossy"),
        ])

        await msg.reply_text(
            f"📋 *Ringkasan EXIF:*\n\n{header_text}{exif_body}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
            reply_to_message_id=msg.message_id,
        )
    finally:
        rate_limiter.release_concurrent(user_id)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler untuk callback tombol inline (Opsi Riset A+B+C & Cleaning)."""
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

    multi_meta = read_multi_group_metadata(data)
    info = multi_meta["raw_info"]
    gps = multi_meta["raw_gps"]
    coords = gps_to_decimal(gps)

    if query.data == "act:research":
        # Evaluasi Opsi B: Lossless vs Lossy
        lossless_bytes, _ = strip_exif_lossless(data)
        lossless_psnr = calculate_psnr(data, lossless_bytes)
        lossless_ssim = calculate_ssim(data, lossless_bytes)

        lossy_bytes, _ = strip_exif_lossy(data)
        lossy_psnr = calculate_psnr(data, lossy_bytes)
        lossy_ssim = calculate_ssim(data, lossy_bytes)

        anomalies_str = "\n".join([f"  • {a}" for a in multi_meta["anomalies"]]) if multi_meta["anomalies"] else "  • Tidak ditemukan anomali."

        research_report = (
            "🔬 *LAPORAN ANALISIS RISET MULTI-OBSERVASI (Q1 Benchmark)*\n\n"
            "🌐 *OPSI A: Survival Metadata Multi-Group*\n"
            f"• EXIF Count: `{multi_meta['exif_count']}` tag\n"
            f"• GPS Status: `{'Ada' if multi_meta['has_gps'] else 'Tidak ada'}`\n"
            f"• XMP Data: `{'Ada' if multi_meta['has_xmp'] else 'Tidak ada'}`\n"
            f"• ICC Profile: `{'Ada' if multi_meta['has_icc_profile'] else 'Tidak ada'}`\n"
            f"• C2PA Manifest: `{'Ada' if multi_meta['has_c2pa'] else 'Tidak ada'}`\n"
            f"• MakerNote: `{'Ada' if multi_meta['has_makernote'] else 'Tidak ada'}`\n\n"

            "🧹 *OPSI B: Benchmark Pembersihan & Kualitas Piksel*\n"
            f"• Lossless Strip: `PSNR={lossless_psnr} dB | SSIM={lossless_ssim}` (Bit-Exact)\n"
            f"• Lossy Strip: `PSNR={lossy_psnr} dB | SSIM={lossy_ssim}`\n\n"

            "🤖 *OPSI C: Forensik AI & Anomali Ketidakcocokan*\n"
            f"• Deteksi Generator AI: `{multi_meta['ai_signature'] or 'Tidak terdeteksi'}`\n"
            f"• Evaluasi Anomali:\n{anomalies_str}"
        )

        await query.message.reply_text(research_report, parse_mode="Markdown")

    elif query.data == "act:gps":
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
            [InlineKeyboardButton("🔬 Laporan Riset A+B+C", callback_data="act:research")],
            [InlineKeyboardButton("📋 Ringkasan", callback_data="act:summary"), InlineKeyboardButton("🧹 Lossless", callback_data="act:clean_lossless"), InlineKeyboardButton("🎨 Lossy", callback_data="act:clean_lossy")]
        ]
        if coords:
            keyboard.insert(1, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps")])

        await query.message.edit_text(
            f"📄 *Data EXIF Lengkap:*\n\n{full_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data == "act:summary":
        compact_text = format_exif_text(info, full_mode=False)
        keyboard = [
            [InlineKeyboardButton("🔬 Laporan Riset A+B+C", callback_data="act:research")],
            [InlineKeyboardButton("📄 Semua tag", callback_data="act:full"), InlineKeyboardButton("🧹 Lossless", callback_data="act:clean_lossless"), InlineKeyboardButton("🎨 Lossy", callback_data="act:clean_lossy")]
        ]
        if coords:
            keyboard.insert(1, [InlineKeyboardButton("📍 Lokasi GPS", callback_data="act:gps")])

        await query.message.edit_text(
            f"📋 *Ringkasan EXIF:*\n\n{compact_text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif query.data in ("act:clean_lossless", "act:clean_lossy"):
        mode = "lossless" if query.data == "act:clean_lossless" else "lossy"
        try:
            cleaned_data, ext = strip_exif_lossless(data) if mode == "lossless" else strip_exif_lossy(data)
            orig_filename = getattr(original.document, "file_name", "image.jpg") if original.document else "image.jpg"
            base_name = os.path.splitext(orig_filename)[0]
            out_filename = f"clean_{mode}_{base_name}.{ext}"

            await query.message.reply_document(
                document=io.BytesIO(cleaned_data),
                filename=out_filename,
                caption=f"✅ Metadata EXIF telah berhasil dihapus (Mode: {mode.title()}).",
            )
        except Exception as e:
            logger.error(f"Gagal menghapus EXIF ({mode}): {e}")
            await query.message.reply_text("Gagal menghapus metadata EXIF.")
