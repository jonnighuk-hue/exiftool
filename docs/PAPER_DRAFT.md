# Metadata in Transit: A Cross-Platform Measurement of EXIF/XMP/C2PA Survival and Residual Leakage in Metadata-Cleaning Tools 📄🔬

**Paper Draft Outline for Scopus Q1 Target Submission**  
*(Target Journals: Forensic Science International: Digital Investigation / Computers & Security / IEEE T-IFS)*

---

## 📌 Abstract
Digital image provenance and metadata privacy are increasingly critical in digital forensics and privacy protection. While instant messaging and social media platforms claim to protect user privacy by scrubbing metadata, the exact survival rates of diverse metadata standards (EXIF, GPS, XMP, IPTC, and C2PA manifests) remain under-measured across different transfer modes (compressed photo vs. uncompressed file). Furthermore, existing metadata-cleaning utilities present unquantified trade-offs between residual metadata leakage and image degradation (PSNR/SSIM). This study presents a systematic empirical evaluation of metadata survival across messaging platforms and benchmarks lossless vs. lossy metadata cleaning algorithms. We introduce a unified evaluation engine and Telegram research artifact (`exiftool-bot`) capable of multi-group metadata extraction, AI signature detection, and anomaly inconsistency analysis. Our findings demonstrate that...

---

## 🎯 1. Introduction
- **Motivation**: Digital image metadata (EXIF, GPS, XMP, C2PA) leaks sensitive user locations and camera fingerprints.
- **Literature Gap**: Existing literature either focuses exclusively on AI-generated image detection or single-platform tests, lacking systematic cross-platform measurement and lossy vs. lossless cleaning trade-off quantification.
- **Key Scientific Contributions**:
  1. Empirical measurement of EXIF/GPS/XMP/C2PA survival rates across messaging platforms under Photo vs Document transfer modes.
  2. Quantitative benchmarking of metadata residual leakage vs. PSNR/SSIM image degradation across Lossless (`piexif`) and Lossy (`re-encode`) cleaning techniques.
  3. Multi-signal forensic analysis combining AI signature detection and camera metadata inconsistency rules.
  4. An open-source, reproducible evaluation benchmark harness and production Telegram Bot artifact.

---

## 🔬 2. Research Questions & Hypotheses
- **RQ1 (Metadata Survival)**: To what extent do EXIF, GPS, XMP, IPTC, and C2PA metadata survive across messaging/social platforms when transferred as compressed photos versus uncompressed documents?
  - *H1*: Compressed photo transfers scrub GPS metadata >95% of the time, whereas document transfers preserve >90% of metadata.
- **RQ2 (Residual Leakage & Quality)**: What is the trade-off between residual metadata leakage and image quality degradation (PSNR/SSIM) when comparing lossless stripping against pixel re-encoding?
  - *H2*: Lossless stripping achieves bit-exact quality (PSNR = $\infty$, SSIM = 1.0) while completely removing EXIF/GPS metadata without spatial distortion.
- **RQ3 (Provenance Impact & Forensic Inconsistencies)**: How does metadata degradation in transit affect AI generator signature detection and provenance validation?
  - *H3*: Metadata stripping drops AI generator recall toward zero, necessitating multi-signal forensic checks (anomalies + pixel analysis).

---

## 📐 3. Methodology & Benchmark Design

### 3.1 Datasets & Ground Truth
- `exif-samples` (ianare/exif-samples): 90+ real-world camera images with verified GPS IFDs.
- `FlickrExif` (HuggingFace CTU-OU/FlickrExif): 350k+ rows of real camera metadata.
- `DoxBench` (HuggingFace MomoUchi/DoxBench): Privacy benchmark dataset.
- Synthetic AI Dataset: Images generated via Stable Diffusion, Midjourney, FLUX, and DALL-E.

### 3.2 Metrics & Statistical Framework
- **Survival Rate**: Wilson Score 95% Confidence Intervals.
- **Image Quality**: Peak Signal-to-Noise Ratio (PSNR) and Structural Similarity Index (SSIM).
- **Paired Statistical Tests**: McNemar test with continuity correction ($\chi^2$) for comparing paired proportion outcomes between cleaning modes.

---

## 📊 4. Experimental Results (Summary)
- **EXIF Presence Rate**: $94.4\%$ (95% CI: $[87.6\%, 97.6\%]$) on raw baseline datasets.
- **GPS Survival Rate**: $23.3\%$ (95% CI: $[15.8\%, 33.1\%]$) on sample camera benchmarks.
- **Lossless vs Lossy Benchmark**:
  - Lossless Stripping: Residual EXIF = 0, PSNR = $\infty$, SSIM = 1.000.
  - Lossy Stripping (Re-encode): Residual EXIF = 0, Mean PSNR = 41.2 dB, SSIM = 0.987.

---

## 🛡️ 5. Ethics, Privacy & Artifact Availability
- All test images are anonymized or sourced from public open datasets.
- Artifact Repository: [github.com/jonnighuk-hue/exiftool](https://github.com/jonnighuk-hue/exiftool)
