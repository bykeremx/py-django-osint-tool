# Görsel metadata / EXIF / GPS çıkarımı (Pillow).
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from PIL import Image, ExifTags
from PIL.ExifTags import GPSTAGS


class ImageMetadataService:
    @classmethod
    def analyze(cls, file_path: str | Path) -> dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            return {"error": "Dosya bulunamadı."}

        try:
            with Image.open(path) as image:
                basic = cls._basic_info(image, path)
                exif = cls._extract_exif(image)
                gps = cls._extract_gps(exif.get("gps_ifd", {}))
                return {
                    "basic": basic,
                    "exif": exif,
                    "gps": gps,
                    "error": None,
                }
        except Exception as e:
            return {"error": f"Metadata okunamadı: {e}"}

    @staticmethod
    def _basic_info(image: Image.Image, path: Path) -> dict[str, Any]:
        width, height = image.size
        return {
            "filename": path.name,
            "format": image.format or "Bilinmiyor",
            "mode": image.mode,
            "width": width,
            "height": height,
            "megapixels": round((width * height) / 1_000_000, 2),
            "has_transparency": image.mode in ("RGBA", "LA", "PA"),
            "is_animated": getattr(image, "is_animated", False),
            "frame_count": getattr(image, "n_frames", 1),
            "dpi": image.info.get("dpi"),
            "icc_profile": "Var" if "icc_profile" in image.info else "Yok",
        }

    @staticmethod
    def _extract_exif(image: Image.Image) -> dict[str, Any]:
        exif_data = image.getexif()
        if not exif_data:
            return {"tags": {}, "raw_tags": {}, "gps_ifd": {}, "count": 0}

        tags: dict[str, str] = {}
        raw_tags: dict[int, Any] = {}
        gps_ifd: dict[Any, Any] = {}

        for tag_id, value in exif_data.items():
            raw_tags[tag_id] = value
            name = ExifTags.TAGS.get(tag_id, str(tag_id))
            tags[name] = ImageMetadataService._stringify(value)

        for ifd_id in ExifTags.IFD:
            try:
                ifd = exif_data.get_ifd(ifd_id)
            except Exception:
                continue
            if ifd_id == ExifTags.IFD.GPSInfo:
                gps_ifd = dict(ifd)
            for tag_id, value in ifd.items():
                if ifd_id == ExifTags.IFD.GPSInfo:
                    name = GPSTAGS.get(tag_id, f"GPS_{tag_id}")
                else:
                    name = ExifTags.TAGS.get(tag_id, str(tag_id))
                if name == "UserComment":
                    tags[name] = ImageMetadataService._decode_user_comment(value)
                else:
                    tags[name] = ImageMetadataService._stringify(value)

        interesting = {
            k: tags[k]
            for k in (
                "Make", "Model", "Software", "DateTime", "DateTimeOriginal",
                "Artist", "Copyright", "ExposureTime", "FNumber", "ISOSpeedRatings",
                "FocalLength", "Flash", "Orientation", "LensModel",
            )
            if k in tags
        }

        return {"tags": interesting, "all_tags": tags, "raw_tags": raw_tags, "gps_ifd": gps_ifd, "count": len(tags)}

    @staticmethod
    def _extract_gps(gps_ifd: dict) -> dict[str, Any]:
        if not gps_ifd:
            return {"available": False}

        decoded = {}
        for key, val in gps_ifd.items():
            decoded[GPSTAGS.get(key, key)] = val

        lat = ImageMetadataService._gps_to_decimal(decoded.get("GPSLatitude"), decoded.get("GPSLatitudeRef"))
        lon = ImageMetadataService._gps_to_decimal(decoded.get("GPSLongitude"), decoded.get("GPSLongitudeRef"))

        return {
            "available": lat is not None and lon is not None,
            "latitude": lat,
            "longitude": lon,
            "altitude": ImageMetadataService._stringify(decoded.get("GPSAltitude")),
            "timestamp": ImageMetadataService._stringify(decoded.get("GPSTimeStamp")),
            "raw": {str(k): ImageMetadataService._stringify(v) for k, v in decoded.items()},
        }

    @staticmethod
    def _gps_to_decimal(coord, ref) -> float | None:
        if not coord or not ref:
            return None
        try:
            degrees = float(coord[0])
            minutes = float(coord[1])
            seconds = float(coord[2])
            decimal = degrees + minutes / 60 + seconds / 3600
            if ref in ("S", "W"):
                decimal = -decimal
            return round(decimal, 6)
        except Exception:
            return None

    @staticmethod
    def _decode_user_comment(value: Any) -> str:
        if isinstance(value, bytes):
            if value.startswith(b"UNICODE\x00\x00"):
                try:
                    return value[8:].decode("utf-16-be", errors="replace")
                except Exception:
                    pass
            if value.startswith(b"ASCII\x00\x00\x00"):
                return value[8:].decode("ascii", errors="replace")
            return value.decode("utf-8", errors="replace")
        return ImageMetadataService._stringify(value)

    @staticmethod
    def _stringify(value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        if isinstance(value, tuple):
            return ", ".join(str(v) for v in value)
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value)
