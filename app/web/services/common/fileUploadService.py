# Ortak dosya yükleme: doğrulama, kayıt, tekrar kullanılabilir sonuç dict.
from __future__ import annotations

import uuid
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile


class FileUploadError(Exception):
    """Yükleme doğrulama veya kayıt hatası."""


class FileUploadService:
    DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tiff", ".tif", ".bmp"}
    IMAGE_CONTENT_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "image/tiff",
        "image/bmp",
    }

    @classmethod
    def save_upload(
        cls,
        uploaded_file: UploadedFile,
        *,
        subfolder: str,
        allowed_extensions: set[str] | None = None,
        allowed_content_types: set[str] | None = None,
        max_bytes: int | None = None,
    ) -> dict:
        """
        Dosyayı MEDIA_ROOT altına kaydeder.
        Dönüş: original_name, stored_name, relative_path, absolute_path, size, content_type
        """
        if not uploaded_file:
            raise FileUploadError("Dosya seçilmedi.")

        max_bytes = max_bytes or cls.DEFAULT_MAX_BYTES
        allowed_extensions = allowed_extensions or cls.IMAGE_EXTENSIONS
        allowed_content_types = allowed_content_types or cls.IMAGE_CONTENT_TYPES

        original = (uploaded_file.name or "upload").strip()
        ext = Path(original).suffix.lower()
        if ext not in allowed_extensions:
            raise FileUploadError(f"İzin verilmeyen uzantı: {ext or '(yok)'}")

        content_type = (uploaded_file.content_type or "").lower()
        if content_type and content_type not in allowed_content_types:
            raise FileUploadError(f"İzin verilmeyen içerik türü: {content_type}")

        size = uploaded_file.size or 0
        if size <= 0:
            raise FileUploadError("Boş dosya yüklenemez.")
        if size > max_bytes:
            raise FileUploadError(f"Dosya çok büyük (max {max_bytes // (1024 * 1024)} MB).")

        media_root = cls._media_root()
        target_dir = media_root / subfolder
        target_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}{ext}"
        absolute_path = target_dir / stored_name
        relative_path = f"{subfolder}/{stored_name}".replace("\\", "/")

        cls._write_file(uploaded_file, absolute_path)

        return {
            "original_name": original,
            "stored_name": stored_name,
            "relative_path": relative_path,
            "absolute_path": str(absolute_path),
            "size": size,
            "content_type": content_type or "application/octet-stream",
            "media_url": cls._media_url(relative_path),
        }

    @classmethod
    def save_image(cls, uploaded_file: UploadedFile, subfolder: str = "uploads/metadata") -> dict:
        """Görsel yükleme kısayolu."""
        return cls.save_upload(
            uploaded_file,
            subfolder=subfolder,
            allowed_extensions=cls.IMAGE_EXTENSIONS,
            allowed_content_types=cls.IMAGE_CONTENT_TYPES,
        )

    @staticmethod
    def _write_file(uploaded_file: UploadedFile, destination: Path) -> None:
        uploaded_file.seek(0)
        with destination.open("wb") as out:
            for chunk in uploaded_file.chunks():
                out.write(chunk)

    @staticmethod
    def _media_root() -> Path:
        from django.conf import settings

        return Path(settings.MEDIA_ROOT)

    @staticmethod
    def _media_url(relative_path: str) -> str:
        from django.conf import settings

        base = settings.MEDIA_URL.rstrip("/")
        return f"{base}/{relative_path}"
