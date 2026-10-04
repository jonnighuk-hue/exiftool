import io
import logging
from PIL import ExifTags, Image, ImageOps
from PIL.ExifTags import GPSTAGS, TAGS
import piexif

from bot.config import MAX_IMAGE_DIMENSION

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


def validate_image_dimensions(img: Image.Image) -> None:
    """Aturan V-4: Memeriksa apakah dimensi gambar melebihi 12.000px per sisi."""
    w, h = img.size
    if w > MAX_IMAGE_DIMENSION or h > MAX_IMAGE_DIMENSION:
        raise ValueError(
            f"Dimensi gambar ({w}x{h}px) melebihi batas maksimal {MAX_IMAGE_DIMENSION}px per sisi."
        )


def read_exif(data: bytes) -> tuple[dict, dict]:
    """Membaca metadata EXIF dan GPS dari data biner gambar (Aturan E-1 & V-4)."""
    img = Image.open(io.BytesIO(data))
    validate_image_dimensions(img)

    exif = img.getexif()
    if not exif:
        return {}, {}

    info = {}
    for tag_id, value in exif.items():
        try:
            tag_name = TAGS.get(tag_id, tag_id)
            info[tag_name] = value
        except Exception:
            continue

    # Exif IFD
    try:
        exif_ifd = exif.get_ifd(ExifTags.IFD.Exif)
        for tag_id, value in exif_ifd.items():
            try:
                tag_name = TAGS.get(tag_id, tag_id)
                info[tag_name] = value
            except Exception:
                continue
    except Exception:
        pass

    # GPS IFD
    gps = {}
    try:
        gps_ifd = exif.get_ifd(ExifTags.IFD.GPSInfo)
        for k, v in gps_ifd.items():
            try:
                tag_name = GPSTAGS.get(k, k)
                gps[tag_name] = v
            except Exception:
                continue
    except Exception:
        pass

    return info, gps


def check_metadata_inconsistencies(info: dict) -> list[str]:
    """Opsi C: Memeriksa anomali dan ketidakcocokan logika pada metadata EXIF."""
    anomalies = []
    make = str(info.get("Make", "")).strip().lower()
    model = str(info.get("Model", "")).strip().lower()
    software = str(info.get("Software", "")).strip().lower()

    # 1. Anomali Perangkat (Make vs Model Mismatch)
    if make and model:
        known_brands = ["apple", "canon", "nikon", "sony", "samsung", "fujifilm", "panasonic", "xiaomi", "google", "huawei", "leica"]
        matched_make_brand = [b for b in known_brands if b in make]
        matched_model_brand = [b for b in known_brands if b in model]
        if matched_make_brand and matched_model_brand and matched_make_brand[0] != matched_model_brand[0]:
            anomalies.append(f"Ketidakcocokan Produsen vs Model Kamera (`{make}` vs `{model}`)")

    # 2. Tag teredit oleh software manipulasi gambar
    editing_tools = ["photoshop", "gimp", "lightroom", "canva", "snapseed", "pixlr"]
    found_editors = [ed.title() for ed in editing_tools if ed in software]
    if found_editors:
        anomalies.append(f"Terdeteksi diproses dengan editor gambar (`{', '.join(found_editors)}`)")

    # 3. Anomali tanpa Make/Model tetapi memiliki tag EXIF dalam jumlah banyak
    if len(info) > 8 and not make and not model:
        anomalies.append("Struktur EXIF kaya tag tetapi tidak memiliki informasi Produsen/Model Kamera")

    return anomalies


def read_multi_group_metadata(data: bytes) -> dict:
    """Ekstraksi Multi-Group Metadata (Opsi A + B + C)."""
    img = Image.open(io.BytesIO(data))
    validate_image_dimensions(img)

    info, gps = read_exif(data)
    
    # Check XMP & ICC Profile
    xmp_raw = img.info.get("xmp") or img.info.get("XML:com.adobe.xmp")
    icc_profile = img.info.get("icc_profile")
    
    # Check C2PA / JUMBF Manifest
    has_c2pa = False
    c2pa_keywords = [b"c2pa", b"jumbf", b"org.contentauthenticity"]
    if any(kw in data.lower() for kw in c2pa_keywords):
        has_c2pa = True

    has_makernote = "MakerNote" in info or any(k for k in info.keys() if "maker" in str(k).lower())

    ai_sig = detect_ai_signature(info)
    anomalies = check_metadata_inconsistencies(info)

    return {
        "has_exif": len(info) > 0,
        "exif_count": len(info),
        "has_gps": len(gps) > 0,
        "gps_coords": gps_to_decimal(gps),
        "has_xmp": xmp_raw is not None,
        "has_icc_profile": icc_profile is not None,
        "has_c2pa": has_c2pa,
        "has_makernote": has_makernote,
        "ai_signature": ai_sig,
        "anomalies": anomalies,
        "raw_info": info,
        "raw_gps": gps,
    }


def detect_ai_signature(info: dict) -> str | None:
    """Memeriksa apakah ada jejak software pembuat AI di metadata EXIF/XMP."""
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
    """Mengonversi koordinat derajat GPS ke format desimal (lat, lon) dengan validasi E-2."""
    try:

        def conv(val, ref):
            d, m, s = (float(x) for x in val)
            deg = d + m / 60.0 + s / 3600.0
            return -deg if ref in ("S", "W") else deg

        lat = conv(gps["GPSLatitude"], gps["GPSLatitudeRef"])
        lon = conv(gps["GPSLongitude"], gps["GPSLongitudeRef"])

        if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
            return None

        return lat, lon
    except (KeyError, TypeError, ValueError, ZeroDivisionError):
        return None


def strip_exif_lossless(data: bytes) -> tuple[bytes, str]:
    """Pembersihan EXIF Lossless (tanpa re-encode piksel) menggunakan piexif.remove."""
    try:
        out = io.BytesIO()
        piexif.remove(data, out)
        return out.getvalue(), "jpg"
    except Exception as e:
        logger.warning(f"Lossless strip failed, falling back to lossy strip: {e}")
        return strip_exif_lossy(data)


def strip_exif_lossy(data: bytes) -> tuple[bytes, str]:
    """Pembersihan EXIF Lossy (re-encode piksel) dengan ImageOps.exif_transpose."""
    img = Image.open(io.BytesIO(data))
    validate_image_dimensions(img)

    fmt = img.format or "JPEG"
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


def strip_exif(data: bytes, mode: str = "lossless") -> tuple[bytes, str]:
    """Fungsi utama pembersihan EXIF (mode: 'lossless' atau 'lossy')."""
    if mode == "lossless":
        return strip_exif_lossless(data)
    else:
        return strip_exif_lossy(data)


def format_exif_text(info: dict, full_mode: bool = False) -> str:
    """Memformat data EXIF menjadi tampilan ringkas atau lengkap."""
    if not info:
        return "Tidak ada data EXIF."

    if not full_mode:
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
                if isinstance(val, bytes):
                    if len(val) > 40:
                        continue
                    val = val.decode("utf-8", errors="ignore")
                val_str = str(val).replace("\n", " ")
                lines.append(f"• *{label}*: `{val_str[:60]}`")

        if not lines:
            for k, v in list(info.items())[:6]:
                if isinstance(v, bytes) and len(v) > 40:
                    continue
                lines.append(f"• *{k}*: `{str(v)[:60]}`")

        return "\n".join(lines)
    else:
        lines = []
        for key, value in info.items():
            if isinstance(value, bytes):
                if len(value) > 40:
                    continue
                value = value.decode("utf-8", errors="ignore")
            val_str = str(value).replace("\n", " ")
            lines.append(f"• *{key}*: `{str(value)[:80]}`")

        return "\n".join(lines)[:3500]
