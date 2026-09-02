# EXIF metadata yazma (JPEG) — piexif + Pillow.
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

import piexif
from piexif import helper
from PIL import Image

from django.conf import settings


class ImageMetadataWriteError(Exception):
    """Metadata yazma hatası."""


class ImageMetadataWriteService:
    JPEG_EXTENSIONS = {".jpg", ".jpeg"}
    MAX_PAYLOAD_BYTES = 64 * 1024

    EDITABLE_FIELDS = (
        "make",
        "model",
        "software",
        "artist",
        "copyright",
        "datetime",
        "datetime_original",
        "image_description",
        "user_comment",
        "script_payload",
        "latitude",
        "longitude",
    )

    @classmethod
    def form_defaults(cls, metadata: dict[str, Any]) -> dict[str, str]:
        tags = metadata.get("exif", {}).get("all_tags", {})
        gps = metadata.get("gps", {})
        user_comment = tags.get("UserComment", "")
        image_desc = tags.get("ImageDescription", "")
        payload = user_comment or image_desc
        return {
            "make": tags.get("Make", ""),
            "model": tags.get("Model", ""),
            "software": tags.get("Software", ""),
            "artist": tags.get("Artist", ""),
            "copyright": tags.get("Copyright", ""),
            "datetime": tags.get("DateTime", ""),
            "datetime_original": tags.get("DateTimeOriginal", ""),
            "image_description": image_desc,
            "user_comment": user_comment,
            "script_payload": payload,
            "latitude": str(gps.get("latitude", "") or ""),
            "longitude": str(gps.get("longitude", "") or ""),
        }

    @classmethod
    def apply(cls, source_path: str | Path, fields: dict[str, str]) -> dict[str, Any]:
        path = Path(source_path).resolve()
        if not path.exists():
            raise ImageMetadataWriteError("Kaynak dosya bulunamadı.")

        ext = path.suffix.lower()
        if ext not in cls.JPEG_EXTENSIONS:
            raise ImageMetadataWriteError(
                "EXIF yazma yalnızca JPEG (.jpg, .jpeg) için desteklenir."
            )

        payload = (fields.get("script_payload") or "").strip()
        user_comment = (fields.get("user_comment") or "").strip()
        if payload:
            user_comment = payload

        image_description = (fields.get("image_description") or "").strip()
        if payload and not image_description and fields.get("mirror_payload_to_description"):
            image_description = payload

        cls._validate_text_length(user_comment, "UserComment / script")
        cls._validate_text_length(image_description, "ImageDescription")

        try:
            exif_dict = piexif.load(str(path))
        except Exception:
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}, "thumbnail": None}

        zeroth = exif_dict.setdefault("0th", {})
        exif_ifd = exif_dict.setdefault("Exif", {})
        gps_ifd = exif_dict.setdefault("GPS", {})

        cls._set_ascii(zeroth, piexif.ImageIFD.Make, fields.get("make"))
        cls._set_ascii(zeroth, piexif.ImageIFD.Model, fields.get("model"))
        cls._set_ascii(zeroth, piexif.ImageIFD.Software, fields.get("software"))
        cls._set_ascii(zeroth, piexif.ImageIFD.Artist, fields.get("artist"))
        cls._set_ascii(zeroth, piexif.ImageIFD.Copyright, fields.get("copyright"))
        cls._set_ascii(zeroth, piexif.ImageIFD.DateTime, fields.get("datetime"))
        cls._set_ascii(zeroth, piexif.ImageIFD.ImageDescription, image_description)

        cls._set_ascii(exif_ifd, piexif.ExifIFD.DateTimeOriginal, fields.get("datetime_original"))
        if user_comment:
            exif_ifd[piexif.ExifIFD.UserComment] = helper.UserComment.dump(user_comment, encoding="unicode")

        lat_raw = (fields.get("latitude") or "").strip()
        lon_raw = (fields.get("longitude") or "").strip()
        if lat_raw and lon_raw:
            try:
                lat = float(lat_raw.replace(",", "."))
                lon = float(lon_raw.replace(",", "."))
                gps_ifd.update(cls._build_gps_ifd(lat, lon))
                exif_dict["GPS"] = gps_ifd
            except ValueError as e:
                raise ImageMetadataWriteError(f"GPS koordinatları geçersiz: {e}") from e
        elif lat_raw or lon_raw:
            raise ImageMetadataWriteError("GPS için hem enlem hem boylam girilmeli.")

        exif_bytes = piexif.dump(exif_dict)
        output_path = cls._output_path(path)

        with Image.open(path) as image:
            if image.mode not in ("RGB", "L"):
                image = image.convert("RGB")
            image.save(output_path, "JPEG", exif=exif_bytes, quality=95)

        relative = output_path.resolve().relative_to(Path(settings.MEDIA_ROOT).resolve())
        relative_str = str(relative).replace("\\", "/")
        base = settings.MEDIA_URL.rstrip("/")

        written = cls._summarize_written(fields, user_comment, image_description, lat_raw, lon_raw)
        return {
            "original_name": path.name,
            "stored_name": output_path.name,
            "relative_path": relative_str,
            "absolute_path": str(output_path),
            "size": output_path.stat().st_size,
            "content_type": "image/jpeg",
            "media_url": f"{base}/{relative_str}",
            "written_fields": written,
        }

    @staticmethod
    def _set_ascii(ifd: dict, tag: int, value: str | None) -> None:
        if value is None:
            return
        text = value.strip()
        if text:
            ifd[tag] = text.encode("ascii", errors="replace")

    @staticmethod
    def _validate_text_length(value: str, label: str) -> None:
        if not value:
            return
        encoded = value.encode("utf-8")
        if len(encoded) > ImageMetadataWriteService.MAX_PAYLOAD_BYTES:
            raise ImageMetadataWriteError(
                f"{label} çok uzun (max {ImageMetadataWriteService.MAX_PAYLOAD_BYTES // 1024} KB)."
            )

    @staticmethod
    def _build_gps_ifd(lat: float, lon: float) -> dict[int, Any]:
        lat_ref = b"N" if lat >= 0 else b"S"
        lon_ref = b"E" if lon >= 0 else b"W"
        return {
            piexif.GPSIFD.GPSLatitudeRef: lat_ref,
            piexif.GPSIFD.GPSLongitudeRef: lon_ref,
            piexif.GPSIFD.GPSLatitude: ImageMetadataWriteService._decimal_to_dms(abs(lat)),
            piexif.GPSIFD.GPSLongitude: ImageMetadataWriteService._decimal_to_dms(abs(lon)),
        }

    @staticmethod
    def _decimal_to_dms(decimal: float) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
        degrees = int(decimal)
        minutes_float = (decimal - degrees) * 60
        minutes = int(minutes_float)
        seconds = round((minutes_float - minutes) * 60 * 100)
        return (degrees, 1), (minutes, 1), (seconds, 100)

    @staticmethod
    def _output_path(source: Path) -> Path:
        edited_name = f"{source.stem}_edited_{uuid.uuid4().hex[:8]}.jpg"
        return source.parent / edited_name

    @staticmethod
    def _summarize_written(
        fields: dict[str, str],
        user_comment: str,
        image_description: str,
        lat: str,
        lon: str,
    ) -> list[str]:
        summary: list[str] = []
        labels = {
            "make": "Make",
            "model": "Model",
            "software": "Software",
            "artist": "Artist",
            "copyright": "Copyright",
            "datetime": "DateTime",
            "datetime_original": "DateTimeOriginal",
        }
        for key, label in labels.items():
            if (fields.get(key) or "").strip():
                summary.append(label)
        if image_description:
            summary.append("ImageDescription")
        if user_comment:
            summary.append("UserComment")
        if (fields.get("script_payload") or "").strip():
            summary.append("ScriptPayload")
        if lat and lon:
            summary.append("GPS")
        return summary
