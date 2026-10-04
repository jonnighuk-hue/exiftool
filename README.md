# Telegram Bot EXIF Inspector & Cleaner 🧹📸

Bot Telegram untuk membaca metadata EXIF, lokasi GPS, dan menghapus EXIF dari foto (JPG, PNG, HEIC).

## 🚀 Fitur
- 🔍 **Membaca EXIF**: Menampilkan kamera, ISO, aperture, resolusi, waktu pengambil gambar, dll.
- 🤖 **Deteksi Metadata AI**: Memindai jejak software pembuat gambar AI (Midjourney, Stable Diffusion, DALL-E, FLUX, Firefly, dll.)
- 📍 **Lokasi GPS & Reverse Geocoding**: Menampilkan lokasi peta, koordinat, dan estimasi nama alamat/wilayah.
- 🧹 **Hapus EXIF (EXIF Cleaner)**: Menghapus seluruh metadata sensitif & mengembalikan file gambar bersih tanpa mengubah orientasi foto.
- 📱 **Dukungan Foto iPhone (HEIC)**: Mendukung format `.heic` dari iPhone.

## 🛠️ Cara Penggunaan & Setup

1. **Install Dependensi**
   ```bash
   pip install -r requirements.txt
   ```

2. **Konfigurasi Environment Variable**
   Buat file `.env` di folder project (bisa menyalin dari `.env.example`):
   ```env
   BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyZ
   ```
   *Dapatkan token bot dari [@BotFather](https://t.me/BotFather) di Telegram.*

3. **Jalankan Bot**
   ```bash
   python bot.py
   ```

## 📝 Catatan Penting
Kirim foto sebagai **File/Dokumen** (bukan sebagai Foto biasa) di Telegram agar Telegram tidak secara otomatis menghapus metadata EXIF sebelum diterima oleh bot.
