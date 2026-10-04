import os
import sys
import json
import time
from glob import glob

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.exif_service import (
    read_multi_group_metadata,
    strip_exif_lossless,
    strip_exif_lossy
)
from benchmark.metrics import (
    calculate_psnr,
    calculate_ssim,
    wilson_score_interval
)
from benchmark.json_reporter import (
    create_benchmark_report,
    generate_image_hashes
)

def run_benchmark_on_folder(sample_folder: str, output_report_path: str = "benchmark_results.json"):
    """
    Menjalankan harness benchmark otomatis (CLI) pada folder sampel gambar.
    Mengukur survival rate metadata (RQ1), kebocoran residual & PSNR/SSIM (RQ2).
    """
    print(f"[+] Running Research Benchmark Harness on folder: {sample_folder}")
    
    image_paths = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.heic", "*.webp"):
        image_paths.extend(glob(os.path.join(sample_folder, "**", ext), recursive=True))

    if not image_paths:
        print(f"[!] No sample images found in: {sample_folder}")
        return

    print(f"[+] Found {len(image_paths)} sample images.")
    
    reports = []
    total_images = len(image_paths)
    exif_survival_count = 0
    gps_survival_count = 0
    c2pa_count = 0
    ai_count = 0

    start_bench = time.time()

    for path in image_paths:
        t0 = time.time()
        with open(path, "rb") as f:
            data = f.read()

        filename = os.path.basename(path)
        try:
            orig_meta = read_multi_group_metadata(data)
        except Exception as e:
            print(f"[!] Error processing {filename}: {e}")
            continue

        if orig_meta["has_exif"]:
            exif_survival_count += 1
        if orig_meta["has_gps"]:
            gps_survival_count += 1
        if orig_meta["has_c2pa"]:
            c2pa_count += 1
        if orig_meta["ai_signature"]:
            ai_count += 1

        # Pembersihan Lossless
        lossless_bytes, _ = strip_exif_lossless(data)
        lossless_meta = read_multi_group_metadata(lossless_bytes)
        lossless_psnr = calculate_psnr(data, lossless_bytes)
        lossless_ssim = calculate_ssim(data, lossless_bytes)

        # Pembersihan Lossy
        lossy_bytes, _ = strip_exif_lossy(data)
        lossy_meta = read_multi_group_metadata(lossy_bytes)
        lossy_psnr = calculate_psnr(data, lossy_bytes)
        lossy_ssim = calculate_ssim(data, lossy_bytes)

        exec_ms = (time.time() - t0) * 1000.0

        report = create_benchmark_report(
            filename=filename,
            original_meta=orig_meta,
            lossless_cleaned_meta=lossless_meta,
            lossy_cleaned_meta=lossy_meta,
            lossless_psnr=lossless_psnr,
            lossy_psnr=lossy_psnr,
            lossless_ssim=lossless_ssim,
            lossy_ssim=lossy_ssim,
            execution_time_ms=exec_ms
        )
        reports.append(report)

    total_time = time.time() - start_bench

    # Stat Wilson 95% CI
    exif_rate, exif_low, exif_high = wilson_score_interval(exif_survival_count, total_images)
    gps_rate, gps_low, gps_high = wilson_score_interval(gps_survival_count, total_images)

    summary = {
        "benchmark_summary": {
            "total_samples": total_images,
            "total_benchmark_time_seconds": round(total_time, 2),
            "exif_presence_rate": {
                "rate": exif_rate,
                "wilson_95ci": [exif_low, exif_high]
            },
            "gps_presence_rate": {
                "rate": gps_rate,
                "wilson_95ci": [gps_low, gps_high]
            },
            "c2pa_detected_count": c2pa_count,
            "ai_signatures_detected_count": ai_count
        },
        "detailed_results": reports
    }

    with open(output_report_path, "w", encoding="utf-8") as out_f:
        json.dump(summary, out_f, indent=2)

    print(f"\n[+] Benchmark Complete!")
    print(f"[*] EXIF Survival Rate: {exif_rate*100:.1f}% (95% CI: [{exif_low*100:.1f}%, {exif_high*100:.1f}%])")
    print(f"[*] GPS Survival Rate: {gps_rate*100:.1f}% (95% CI: [{gps_low*100:.1f}%, {gps_high*100:.1f}%])")
    print(f"[*] Structured Report Saved To: {output_report_path}")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else os.path.join("exif-samples", "jpg")
    run_benchmark_on_folder(folder)
