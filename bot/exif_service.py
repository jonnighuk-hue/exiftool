import io
import logging
from PIL import ExifTags, Image, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS

logger = logging.getLogger(__name__)

# Register HEIC opener if available
try:
    from pillow_heif import register_heif_opener

    register_heif_opener()
except ImportError:
    logger.info("pillow-heif tidak terinstall. Support HEIC tidak aktif.")


AI_EXIF_SIGNATURES = {
    "stable diffusion": "Stable Diffusion",
    "midjourney": "Midjourney",
    "dall-e": "DALL-E",
    "dall·e": "DALL-E",
    "comfyui": "ComfyUI / SD",
    "automatic1111": "Automatic1111 WebUI",
    "generative": "Generative AI",
    "diffusion": "Diffusion Model",
    "novelai": "NovelAI",
    "firefly": "Adobe Firefly",
    "imagen": "Google Imagen",
    "gemini": "Google Gemini",
    "flux": "FLUX (BFL)",
    "ideogram": "Ideogram",
    "leonardo": "Leonardo.ai",
    "adobe ai": "Adobe AI",
    "ai generated": "Generic AI",
    "synthid": "Google SynthID",
    "bing": "Bing Image Creator",
    "copilot": "Microsoft Copilot AI",
}


def read_exif(data: bytes) -> tuple[dict, dict]:
    """Membaca metadata EXIF dan GPS dari data biner gambar."""
    img = Image.open(io.BytesIO(data))
    exif = img.getexif()
    if not exif:
        return {}, {}

    info = {}
    for tag_id, value in exif.items():
        tag_name = TAGS.get(tag_id, tag_id)
        info[tag_name] = value

    # Exif IFD
    try:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        for tag_id, value in exif_ifd.items():
            tag_name = TAGS.get(tag_id, tag_id)
            info[tag_name] = value
    except Exception:
        pass

    # GPS IFD
    gps = {}
    try:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        gps = {GPSTAGS.get(k, k): v for k, v in gps_ifd.items()}
    except Exception:
        pass

    return info, gps


def detect_ai_signature(info: dict) -> str | None:
    """Memeriksa apakah ada jejak software pembuat AI di metadata EXIF."""
    searchable = [
        str(info.get("Software", "")).lower(),
        str(info.get("ImageDescription", "")).lower(),
        str(info.get("Artist", "")).lower(),
        str(info.get("Copyright", "")).lower(),
        str(info.get("UserComment", "")).lower(),
        str(info.get("XPComment", "")).lower(),
    ]
    combined_text = " ".join(searchable)
    for kw, source_name in AI_EXIF_SIGNATURES.items():
        if kw in combined_text:
            return source_name
    return None


def gps_to_decimal(gps: dict) -> tuple[float, float] | None:
    """Mengonversi koordinat derajat GPS ke format desimal (lat, lon)."""
    try:

        def conv(val, ref):
            d, m, s = (float(x) for x in val)
            deg = d + m / 60.0 + s / 3600.0
            return -deg if ref in ("S", "W") else deg

        lat = conv(gps["GPSLatitude"], gps["GPSLatitudeRef"])
        lon = conv(gps["GPSLongitude"], gps["GPSLongitudeRef"])
        return lat, lon
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def strip_exif(data: bytes) -> tuple[bytes, str]:
    """Menghapus metadata EXIF dengan aman.

    Melakukan transpose orientasi terlebih dahulu agar foto tidak terputar.
    """
    img = Image.open(io.BytesIO(data))
    fmt = img.format or "JPEG"

    # Koreksi rotasi berdasarkan EXIF sebelum metadata dihapus
    img = ImageOps.exif_transpose(img)

    out = io.BytesIO()

    save_fmt = fmt.upper()
    ext = fmt.lower()
    if save_fmt in ("HEIF", "HEIC"):
        save_fmt = "JPEG"
        ext = "jpg"
    elif save_fmt == "JPEG" and img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    img.save(out, format=save_fmt)

    filename_ext = "jpg" if ext in ("jpg", "jpeg") else (ext if ext in ("png", "webp") else "jpg")
    return out.getvalue(), filename_ext


def format_exif_text(info: dict, full_mode: bool = False) -> str:
    """Memformat data EXIF menjadi tampilan ringkas atau lengkap."""
    if not info:
        return "Tidak ada data EXIF."

    if not full_mode:
        # Mode Ringkas (Friendly Summary)
        summary_tags = [
            ("Make", "Perangkat"),
            ("Model", "Model Kamera"),
            ("DateTimeOriginal", "Waktu Pengambilan"),
            ("ExposureTime", "Waktu Eksposur"),
            ("FNumber", "Aperture (f-stop)"),
            ("ISOSpeedRatings", "ISO"),
            ("FocalLength", "Panjang Fokal"),
            ("LensModel", "Lensa"),
            ("Software", "Software"),
        ]
        lines = []
        for tag_key, label in summary_tags:
            val = info.get(tag_key)
            if val is not None:
                val_str = str(val).replace("\n", " ")
                lines.append(f"• *{label}*: `{val_str[:60]}`")

        if not lines:
            # Fallback jika tag ringkas tidak ditemukan
            for k, v in list(info.items())[:6]:
                lines.append(f"• *{k}*: `{str(v)[:60]}`")

        return "\n".join(lines)
    else:
        # Mode Lengkap (Semua Tag)
        lines = []
        for key, value in info.items():
            if isinstance(value, bytes):
                if len(value) > 40:
                    continue
                value = value.decode("utf-8", errors="ignore")
            val_str = str(value).replace("\n", " ")
            lines.append(f"• *{key}*: `{val_str[:80]}`")

        return "\n".join(lines)[:3500]
