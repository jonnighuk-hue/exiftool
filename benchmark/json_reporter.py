import json
import hashlib
import time

def generate_image_hashes(data: bytes) -> dict:
    """Menghitung hash SHA-256 dan MD5 untuk integritas reproduktibilitas riset (RQ1 & RQ2)."""
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "md5": hashlib.md5(data).hexdigest(),
        "size_bytes": len(data)
    }

def create_benchmark_report(
    filename: str,
    original_meta: dict,
    lossless_cleaned_meta: dict,
    lossy_cleaned_meta: dict,
    lossless_psnr: float,
    lossy_psnr: float,
    lossless_ssim: float,
    lossy_ssim: float,
    execution_time_ms: float
) -> dict:
    """Menghasilkan laporan JSON terstruktur berbasis skema tetap untuk analisis riset Q1."""
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "file_name": filename,
        "original_metadata": {
            "has_exif": original_meta.get("has_exif", False),
            "exif_count": original_meta.get("exif_count", 0),
            "has_gps": original_meta.get("has_gps", False),
            "gps_coords": original_meta.get("gps_coords"),
            "has_xmp": original_meta.get("has_xmp", False),
            "has_icc_profile": original_meta.get("has_icc_profile", False),
            "has_c2pa": original_meta.get("has_c2pa", False),
            "has_makernote": original_meta.get("has_makernote", False),
            "ai_signature": original_meta.get("ai_signature")
        },
        "evaluation": {
            "lossless_mode": {
                "residual_exif_count": lossless_cleaned_meta.get("exif_count", 0),
                "residual_gps": lossless_cleaned_meta.get("has_gps", False),
                "psnr_db": lossless_psnr,
                "ssim": lossless_ssim,
                "is_bit_exact": lossless_psnr == float("inf")
            },
            "lossy_mode": {
                "residual_exif_count": lossy_cleaned_meta.get("exif_count", 0),
                "residual_gps": lossy_cleaned_meta.get("has_gps", False),
                "psnr_db": lossy_psnr,
                "ssim": lossy_ssim,
                "is_bit_exact": lossy_psnr == float("inf")
            }
        },
        "benchmark_execution_ms": round(execution_time_ms, 2)
    }
