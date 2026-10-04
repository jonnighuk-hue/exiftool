import logging
import urllib.parse
import urllib.request
import json
from functools import lru_cache
from bot.config import ENABLE_REVERSE_GEOCODING, NOMINATIM_USER_AGENT

logger = logging.getLogger(__name__)

@lru_cache(maxsize=256)
def reverse_geocode(lat: float, lon: float) -> str | None:
    """
    Mengubah koordinat GPS (latitude, longitude) menjadi nama alamat/lokasi
    menggunakan Nominatim OpenStreetMap API dengan caching.
    """
    if not ENABLE_REVERSE_GEOCODING:
        return None

    # Bulatkan koordinat untuk caching efisien
    lat_round = round(lat, 5)
    lon_round = round(lon, 5)

    url = (
        f"https://nominatim.openstreetmap.org/reverse?"
        f"format=jsonv2&lat={lat_round}&lon={lon_round}&zoom=18&addressdetails=1"
    )

    headers = {"User-Agent": NOMINATIM_USER_AGENT}
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                display_name = data.get("display_name")
                if display_name:
                    return display_name
                
                # Alternate fallback from address components
                addr = data.get("address", {})
                parts = [
                    addr.get("road") or addr.get("suburb"),
                    addr.get("city") or addr.get("town") or addr.get("county"),
                    addr.get("state"),
                    addr.get("country")
                ]
                clean_parts = [p for p in parts if p]
                if clean_parts:
                    return ", ".join(clean_parts)
    except Exception as e:
        logger.warning(f"Reverse geocoding error ({lat}, {lon}): {e}")

    return None
