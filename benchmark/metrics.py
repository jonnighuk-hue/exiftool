import io
import math
import numpy as np
from PIL import Image
from scipy.stats import chisquare


def calculate_psnr(img1_bytes: bytes, img2_bytes: bytes) -> float:
    """Menghitung PSNR (Peak Signal-to-Noise Ratio) antara dua gambar."""
    img1 = Image.open(io.BytesIO(img1_bytes)).convert("RGB")
    img2 = Image.open(io.BytesIO(img2_bytes)).convert("RGB")

    # Pastikan ukuran sama
    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    mse = np.mean((arr1 - arr2) ** 2)
    if mse == 0:
        return float("inf")  # Bit-for-bit identical

    max_pixel = 255.0
    psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
    return round(psnr, 2)


def calculate_ssim(img1_bytes: bytes, img2_bytes: bytes) -> float:
    """Menghitung SSIM (Structural Similarity Index) sederhana antara dua gambar."""
    img1 = Image.open(io.BytesIO(img1_bytes)).convert("L")
    img2 = Image.open(io.BytesIO(img2_bytes)).convert("L")

    if img1.size != img2.size:
        img2 = img2.resize(img1.size)

    arr1 = np.array(img1, dtype=np.float64)
    arr2 = np.array(img2, dtype=np.float64)

    mu1 = arr1.mean()
    mu2 = arr2.mean()
    var1 = arr1.var()
    var2 = arr2.var()
    cov = np.cov(arr1.flat, arr2.flat)[0, 1]

    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    ssim = ((2 * mu1 * mu2 + c1) * (2 * cov + c2)) / ((mu1**2 + mu2**2 + c1) * (var1 + var2 + c2))
    return round(float(ssim), 4)


def wilson_score_interval(successes: int, total: int, confidence: float = 0.95) -> tuple[float, float, float]:
    """Menghitung Interval Kepercayaan Wilson (Wilson Score 95% Confidence Interval) untuk proporsi survival metadata."""
    if total == 0:
        return 0.0, 0.0, 0.0

    z = 1.95996  # 95% confidence
    p = successes / total

    denominator = 1 + z**2 / total
    centre_adjusted_probability = p + z**2 / (2 * total)
    adjusted_std_dev = math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total)

    lower_bound = (centre_adjusted_probability - z * adjusted_std_dev) / denominator
    upper_bound = (centre_adjusted_probability + z * adjusted_std_dev) / denominator

    return round(p, 4), max(0.0, round(lower_bound, 4)), min(1.0, round(upper_bound, 4))


def mcnemar_test(b: int, c: int) -> tuple[float, float]:
    """Uji McNemar untuk perbandingan berpasangan (paired proportion comparison).

    b: Kasus di mana Metode A berhasil, Metode B gagal
    c: Kasus di mana Metode A gagal, Metode B berhasil
    Returns: (statistic, p_value)
    """
    if b + c == 0:
        return 0.0, 1.0

    # Continuity corrected McNemar statistic
    stat = (abs(b - c) - 1) ** 2 / (b + c)
    # Approximation p-value using chi-square distribution with 1 DOF
    p_val = chisquare([b, c]).pvalue
    return round(stat, 4), round(p_val, 5)
