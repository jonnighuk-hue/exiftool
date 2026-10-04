import os
import unittest
from bot.exif_service import (
    read_exif,
    detect_ai_signature,
    gps_to_decimal,
    strip_exif,
    format_exif_text
)
from bot.ratelimit import MemoryRateLimiter

class TestExifService(unittest.TestCase):

    def setUp(self):
        self.sample_gps_path = os.path.join("exif-samples", "jpg", "gps", "DSCN0010.jpg")
        self.sample_canon_path = os.path.join("exif-samples", "jpg", "Canon_40D.jpg")

    def test_gps_sample(self):
        if not os.path.exists(self.sample_gps_path):
            self.skipTest("Sample file DSCN0010.jpg not found")

        with open(self.sample_gps_path, "rb") as f:
            data = f.read()

        info, gps = read_exif(data)
        self.assertIsNotNone(gps)
        
        coords = gps_to_decimal(gps)
        self.assertIsNotNone(coords)
        lat, lon = coords
        self.assertAlmostEqual(lat, 43.467448, places=4)
        self.assertAlmostEqual(lon, 11.885127, places=4)

    def test_strip_exif(self):
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

        real_info = {"Make": "Canon", "Model": "EOS 40D"}
        self.assertIsNone(detect_ai_signature(real_info))

    def test_rate_limiter(self):
        limiter = MemoryRateLimiter(calls=2, window=60)
        user_id = 999
        
        allowed1, _ = limiter.is_allowed(user_id)
        allowed2, _ = limiter.is_allowed(user_id)
        allowed3, wait = limiter.is_allowed(user_id)
        
        self.assertTrue(allowed1)
        self.assertTrue(allowed2)
        self.assertFalse(allowed3)
        self.assertGreater(wait, 0)

if __name__ == "__main__":
    unittest.main()
