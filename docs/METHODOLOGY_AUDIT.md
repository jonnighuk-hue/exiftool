# Audit Ilmiah Benchmark, Metodologi, & Validasi Statistik (Scopus Q1 Standard) 📑🔬

Dokumen ini berisi audit metodologis komprehensif untuk proyek riset **EXIF Tool Benchmark**, memastikan setiap klaim ilmiah didukung oleh definisi penyebut (*denominator*) yang presisi, uji statistik inferensial (*McNemar Test & Effect Size*), dan pembatasan generalisasi yang valid.

---

## 📌 1. Definisi Penyebut & Stratifikasi Sampel (Sample Stratification)

### Celah Metodologis Sebelumnya:
Klaim awal `94.4% EXIF presence` dari 90 sampel dalam satu folder campuran `exif-samples/jpg` memicu **bias sampel (sampling bias)**. Reviewer Scopus Q1 akan menolak klaim agregat seperti ini karena penyebutnya tidak distratifikasi secara homogen.

### Solusi Stratifikasi Sampel (Formal Denominator):
Seluruh sampel gambar wajib dikelompokkan ke dalam 4 strata terpisah dengan denominator $N_k$ masing-masing:

$$\text{Total Sample } N = N_{\text{smartphone}} + N_{\text{camera}} + N_{\text{edited}} + N_{\text{ai}}$$

| Strata ($k$) | Deskripsi Strata | Karakteristik Metadata Inherent | Contoh Sumber Data |
| :--- | :--- | :--- | :--- |
| **Strata 1: Smartphone Native** | Foto langsung dari HP (iPhone, Samsung, Pixel) dengan GPS aktif. | Mengandung EXIF lengkap, GPS IFD, MakerNotes HP, ICC Profile. | Pengambilan mandiri berpersetujuan / `exif-samples/jpg/gps/` |
| **Strata 2: Pro Camera DSLR/RAW** | Foto dari kamera profesional (Canon EOS, Nikon, Sony Alpha). | EXIF kaya tag (lensa, aperture, shutter), tanpa GPS (kecuali modul GPS eksternal). | `FlickrExif` dataset / `exif-samples/jpg/Canon_40D.jpg` |
| **Strata 3: Edited & Web Processed** | Foto yang telah diekspor dari Photoshop, Lightroom, Canva, atau Web. | XMP metadata dominan, tag EXIF parsial/stripped, Software tag terisi. | DoxBench / FlickrExif web-processed |
| **Strata 4: Synthetic AI Outputs** | Gambar buatan model generatif (Stable Diffusion, Midjourney, FLUX, DALL-E 3). | C2PA/JUMBF Manifest, IPTC `DigitalSourceType`, `UserComment` prompt info. | Generated dataset / HuggingFace AI images |

---

## 📊 2. Kerangka Statistik Inferensial (Statistical Rigor)

### 2.1 Interval Kepercayaan Wilson 95% (Wilson Score 95% CI)
Untuk setiap proporsi kehadiran metadata $p = \frac{x}{N}$, interval kepercayaan dihitung tanpa mengasumsikan distribusi normal (terutama untuk proporsi mendekati 0 atau 1):

$$P_{\text{lower}}, P_{\text{upper}} = \frac{p + \frac{z^2}{2N} \pm z \sqrt{\frac{p(1-p)}{N} + \frac{z^2}{4N^2}}}{1 + \frac{z^2}{N}}$$

di mana $z = 1.95996$ (konfidesi 95%).

### 2.2 Uji Hipotesis Berpasangan (McNemar Test with Edwards' Correction)
Untuk menguji perbedaan bermakna antara dua perlakuan pada sampel yang sama (misalnya: Mode Transfer Foto vs File, atau Pembersihan Lossless vs Lossy):

$$\chi^2 = \frac{(|b - c| - 1)^2}{b + c}, \quad df = 1$$

- **$b$**: Kasus di mana Metode A berhasil mempertahankan metadata, tetapi Metode B gagal.
- **$c$**: Kasus di mana Metode A gagal, tetapi Metode B berhasil.
- **Tingkat Signifikansi**: $\alpha = 0.05$ ($p < 0.05$ menunjukkan perbedaan signifikan secara statistik).

### 2.3 Ukuran Efek (Effect Size: Odds Ratio & Cohen's $g$)
Untuk mengukur seberapa besar dampak perbedaan antar metode (bukan hanya nilai-$p$):

$$\text{Odds Ratio (OR)} = \frac{b}{c}$$

$$\text{Cohen's } g = \frac{b}{b + c} - 0.5$$

- $|g| < 0.05$: Efek diabaikan (*negligible*).
- $0.05 \le |g| < 0.15$: Efek kecil (*small*).
- $0.15 \le |g| < 0.25$: Efek sedang (*medium*).
- $|g| \ge 0.25$: Efek besar (*large*).

---

## 📐 3. Validasi Indikator Kualitas Gambar (PSNR & SSIM)

### Peringatan Klaim "PSNR = $\infty$":
- Klaim $\text{PSNR} = \infty$ **hanya valid** pada mode pembersihan **Lossless (`piexif.remove`)** di mana piksel terbukti identik bit-by-bit ($\text{MSE} = 0$).
- Pada mode pembersihan **Lossy (`Pillow` re-encode)**, re-encoding kompresi JPEG akan menyebabkan perbedaan piksel ($\text{MSE} > 0$), sehingga PSNR berkisar antara **38 dB hingga 45 dB**.

---

## 🛡️ 4. Batasan Klaim Forensik AI (Preventing Overclaiming)

### Pernyataan Keterbatasan Ilmiah:
> *"Deteksi gambar AI berbasis metadata EXIF/XMP hanya mendeteksi tag buatan yang secara eksplisit ditinggalkan oleh generator (seperti software prompt Automatic1111 atau manifest C2PA). Metadata yang telah dihapus atau dipalsukan tidak dapat dijadikan bukti tunggal keaslian gambar, sehingga pemeriksaan berbasis metadata wajib dipadukan dengan analisis piksel forensik."*
