import os
import unittest
from PIL import Image
import io

from bot.exif_service import (
    read_exif,
    detect_ai_signature,
    gps_to_decimal,
    strip_exif,
    format_exif_text,
    validate_image_dimensions,
)
from bot.ratelimit import MemoryRateLimiter

class TestExifService(unittest.TestCase):

    def setUp(self):
        self.sample_gps_path = os.path.join("exif-samples", "jpg", "gps", "DSCN0010.jpg")

    def test_valid_gps(self):
        """K-5 Test: GPS Valid."""
        if not os.path.exists(self.sample_gps_path):
            self.skipTest("Sample file DSCN0010.jpg not found")

        with open(self.sample_gps_path, "rb") as f:
            data = f.read()

        info, gps = read_exif(data)
        coords = gps_to_decimal(gps)
        self.assertIsNotNone(coords)
        lat, lon = coords
        self.assertTrue(-90.0 <= lat <= 90.0)
        self.assertTrue(-180.0 <= lon <= 180.0)

    def test_out_of_range_gps(self):
        """K-5 & E-2 Test: GPS di luar rentang valid (-90..90, -180..180)."""
        invalid_gps = {
            "GPSLatitude": (150.0, 0.0, 0.0),
            "GPSLatitudeRef": "N",
            "GPSLongitude": (45.0, 0.0, 0.0),
            "GPSLongitudeRef": "E"
        }
        coords = gps_to_decimal(invalid_gps)
        self.assertIsNone(coords)

    def test_no_exif(self):
        """K-5 Test: Gambar tanpa EXIF."""
        img = Image.new("RGB", (100, 100), color="red")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        
        info, gps = read_exif(buf.getvalue())
        self.assertEqual(len(info), 0)
        self.assertEqual(len(gps), 0)

    def test_dimension_limit(self):
        """K-5 & V-4 Test: Gambar di atas batas dimensi 12.000px per sisi."""
        large_img = Image.new("RGB", (12501, 100), color="blue")
        with self.assertRaises(ValueError):
            validate_image_dimensions(large_img)

    def test_strip_exif(self):
        """K-5 Test: Hapus EXIF."""
        if not os.path.exists(self.sample_gps_path):
            self.skipTest("Sample file DSCN0010.jpg not found")

        with open(self.sample_gps_path, "rb") as f:
            data = f.read()

        cleaned_data, ext = strip_exif(data)
        self.assertEqual(ext, "jpg")
        
        info, gps = read_exif(cleaned_data)
        self.assertEqual(len(info), 0)
        self.assertEqual(len(gps), 0)

    def test_ai_signature_detector(self):
        ai_info = {"Software": "Generated with Stable Diffusion v1.5"}
        detected = detect_ai_signature(ai_info)
        self.assertEqual(detected, "Stable Diffusion")

    def test_rate_limiter_hold(self):
        """K-5 Test: Rate limiter & temporary hold."""
        limiter = MemoryRateLimiter()
        user_id = 888
        
        # Test concurrent acquire/release (R-2)
        self.assertTrue(limiter.acquire_concurrent(user_id))
        self.assertTrue(limiter.acquire_concurrent(user_id))
        self.assertFalse(limiter.acquire_concurrent(user_id))  # Max 2 concurrent
        limiter.release_concurrent(user_id)
        self.assertTrue(limiter.acquire_concurrent(user_id))

if __name__ == "__main__":
    unittest.main()
