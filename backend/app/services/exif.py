import logging
from datetime import datetime, timedelta
from typing import Tuple, Optional
import math
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import io

from app.core.time import utc_now

logger = logging.getLogger(__name__)


class ExifService:
    @staticmethod
    def extract_metadata(file_content: bytes) -> dict:
        metadata = {"timestamp": utc_now(), "lat": None, "lng": None}
        try:
            image = Image.open(io.BytesIO(file_content))
            exif = image.getexif()
            if not exif:
                return metadata

            for tag, value in exif.items():
                decoded = TAGS.get(tag, tag)
                if decoded == "DateTimeOriginal":
                    metadata["timestamp"] = datetime.strptime(
                        value, "%Y:%m:%d %H:%M:%S"
                    )
                elif decoded == "GPSInfo":
                    gps_data = {}
                    for t in value:
                        sub_decoded = GPSTAGS.get(t, t)
                        gps_data[sub_decoded] = value[t]

                    if "GPSLatitude" in gps_data and "GPSLatitudeRef" in gps_data:
                        metadata["lat"] = ExifService._convert_to_degrees(
                            gps_data["GPSLatitude"]
                        )
                        if gps_data["GPSLatitudeRef"] != "N":
                            metadata["lat"] = -metadata["lat"]

                    if "GPSLongitude" in gps_data and "GPSLongitudeRef" in gps_data:
                        metadata["lng"] = ExifService._convert_to_degrees(
                            gps_data["GPSLongitude"]
                        )
                        if gps_data["GPSLongitudeRef"] != "E":
                            metadata["lng"] = -metadata["lng"]
        except Exception as e:
            logger.warning("EXIF extraction failed: %s", e)

        return metadata

    @staticmethod
    def _convert_to_degrees(value):
        d = float(value[0])
        m = float(value[1])
        s = float(value[2])
        return d + (m / 60.0) + (s / 3600.0)

    @staticmethod
    def validate_proximity(
        issue_lat: float,
        issue_lng: float,
        exif_lat: Optional[float],
        exif_lng: Optional[float],
        threshold_m: float = 5.0,
    ) -> bool:
        if exif_lat is None or exif_lng is None:
            return False

        # Haversine distance
        R = 6371000
        phi1, phi2 = math.radians(issue_lat), math.radians(exif_lat)
        dphi = math.radians(exif_lat - issue_lat)
        dlamb = math.radians(exif_lng - issue_lng)

        a = (
            math.sin(dphi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(dlamb / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        return distance <= threshold_m

    @staticmethod
    def validate_timestamp(exif_time: datetime, threshold_days: int = 7) -> bool:
        now = utc_now()
        return (now - exif_time) <= timedelta(days=threshold_days)
