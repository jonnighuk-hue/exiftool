import io
import math
import numpy as np
from PIL import Image
from scipy.stats import chi2


def calculate_psnr(img1_bytes: bytes, img2_bytes: bytes) -> float:
    """Menghitung PSNR (Peak Signal-to-Noise Ratio) antara dua gambar."""
    try:
        img1 = Image.open(io.BytesIO(img1_bytes)).convert("RGB")
        img2 = Image.open(io.BytesIO(img2_bytes)).convert("RGB")
    except Exception:
        return 0.0

    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.BILINEAR)

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    mse = np.mean((arr1 - arr2) ** 2)
    if mse < 1e-10:
        return float("inf")  # Bit-for-bit identical

    max_pixel = 255.0
    psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
    return round(psnr, 2)


def calculate_ssim(img1_bytes: bytes, img2_bytes: bytes) -> float:
    """Menghitung SSIM (Structural Similarity Index) standar antara dua gambar."""
    try:
        img1 = Image.open(io.BytesIO(img1_bytes)).convert("L")
        img2 = Image.open(io.BytesIO(img2_bytes)).convert("L")
    except Exception:
        return 0.0

    if img1.size != img2.size:
        img2 = img2.resize(img1.size, Image.Resampling.BILINEAR)

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    mu1 = arr1.mean()
    mu2 = arr2.mean()
    var1 = arr1.var()
    var2 = arr2.var()
    cov = np.cov(arr1.flat, arr2.flat)[0, 1]

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    ssim = ((2 * mu1 * mu2 + c1) * (2 * cov + c2)) / (
        (mu1**2 + mu2**2 + c1) * (var1 + var2 + c2)
    )
    return round(float(ssim), 4)


def wilson_score_interval(
    successes: int, total: int, confidence: float = 0.95
) -> tuple[float, float, float]:
    """Menghitung Interval Kepercayaan Wilson 95% (Wilson Score 95% CI) untuk proporsi survival metadata."""
    if total == 0:
        return 0.0, 0.0, 0.0

    z = 1.95996  # 95% confidence level
    p = successes / total

    denominator = 1 + z**2 / total
    centre_adjusted = p + z**2 / (2 * total)
    adjusted_std_dev = math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)

    lower_bound = (centre_adjusted - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted + z * adjusted_std_dev) / denominator

    return (
        round(p, 4),
        max(0.0, round(lower_bound, 4)),
        min(1.0, round(upper_bound, 4)),
    )


def mcnemar_test_with_effect_size(
    b: int, c: int
) -> dict:
    """Uji McNemar dengan Koreksi Kontinuitas Edwards & Ukuran Efek (Odds Ratio & Cohen's g).

    b: Jumlah kasus di mana Metode A berhasil, tetapi Metode B gagal.
    c: Jumlah kasus di mana Metode A gagal, tetapi Metode B berhasil.
    """
    total_discordant = b + c
    if total_discordant == 0:
        return {
            "statistic": 0.0,
            "p_value": 1.0,
            "odds_ratio": 1.0,
            "cohens_g": 0.0,
            "is_statistically_significant": False,
        }

    # Continuity corrected McNemar statistic (Edwards correction)
    stat = (abs(b - c) - 1.0) ** 2 / total_discordant
    p_val = float(chi2.sf(stat, df=1))

    # Odds Ratio & Cohen's g
    odds_ratio = (b / c) if c > 0 else float("inf")
    cohens_g = (b / total_discordant) - 0.5

    return {
        "statistic": round(float(stat), 4),
        "p_value": round(p_val, 6),
        "odds_ratio": round(odds_ratio, 3) if odds_ratio != float("inf") else "inf",
        "cohens_g": round(float(cohens_g), 4),
        "is_statistically_significant": p_val < 0.05,
    }
