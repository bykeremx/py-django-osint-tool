from pathlib import Path

from django.conf import settings
from django.shortcuts import render

from app.web.services.common.fileUploadService import FileUploadError, FileUploadService
from app.web.services.image.imageMetadataService import ImageMetadataService
from app.web.services.image.imageMetadataWriteService import (
    ImageMetadataWriteError,
    ImageMetadataWriteService,
)
from app.web.views.analiz.helpers import attach_analiz


def index(request):
    context: dict = {}

    if request.method != "POST":
        return render(request, "pages/image_osint.html", context)

    action = request.POST.get("action", "analyze")
    if action == "apply_metadata":
        return _apply_metadata(request, context)

    return _analyze_upload(request, context)


def _analyze_upload(request, context: dict):
    uploaded = request.FILES.get("image")
    if not uploaded:
        context["error"] = "Lütfen bir görsel seçin."
        return render(request, "pages/image_osint.html", context)

    try:
        file_info = FileUploadService.save_image(uploaded)
        metadata = ImageMetadataService.analyze(file_info["absolute_path"])
        if metadata.get("error"):
            context["error"] = metadata["error"]
        else:
            context["file"] = file_info
            context["metadata"] = metadata
            context["edit_form"] = ImageMetadataWriteService.form_defaults(metadata)
            context["can_write_exif"] = _can_write_exif(file_info["absolute_path"])
            _attach_image_analiz(context)
    except FileUploadError as e:
        context["error"] = str(e)
    except Exception as e:
        context["error"] = str(e)

    return render(request, "pages/image_osint.html", context)


def _apply_metadata(request, context: dict):
    relative_path = (request.POST.get("source_path") or "").strip()
    try:
        source_path = _resolve_media_path(relative_path)
        fields = _collect_edit_fields(request.POST)
        edited = ImageMetadataWriteService.apply(source_path, fields)
        metadata = ImageMetadataService.analyze(edited["absolute_path"])

        context["success"] = "Metadata başarıyla yazıldı. Düzenlenmiş görseli indirebilirsiniz."
        context["edited_file"] = edited
        context["file"] = edited
        context["metadata"] = metadata
        context["edit_form"] = ImageMetadataWriteService.form_defaults(metadata)
        context["can_write_exif"] = True
        context["source_file"] = {
            "relative_path": relative_path,
            "absolute_path": str(source_path),
        }
        _attach_image_analiz(context)
    except (FileUploadError, ImageMetadataWriteError) as e:
        context["error"] = str(e)
        _restore_context_after_edit_error(request, context, relative_path)
    except Exception as e:
        context["error"] = str(e)
        _restore_context_after_edit_error(request, context, relative_path)

    return render(request, "pages/image_osint.html", context)


def _restore_context_after_edit_error(request, context: dict, relative_path: str) -> None:
    context["edit_form"] = _collect_edit_fields(request.POST)
    context["can_write_exif"] = True
    try:
        source_path = _resolve_media_path(relative_path)
        metadata = ImageMetadataService.analyze(source_path)
        if not metadata.get("error"):
            context["metadata"] = metadata
            context["file"] = {
                "relative_path": relative_path,
                "absolute_path": str(source_path),
                "media_url": _media_url_for(relative_path),
                "original_name": source_path.name,
                "size": source_path.stat().st_size,
                "content_type": "image/jpeg",
            }
    except Exception:
        pass


def _collect_edit_fields(post) -> dict[str, str]:
    keys = ImageMetadataWriteService.EDITABLE_FIELDS
    fields = {key: (post.get(key) or "").strip() for key in keys}
    fields["mirror_payload_to_description"] = post.get("mirror_payload_to_description") == "on"
    return fields


def _resolve_media_path(relative_path: str) -> Path:
    if not relative_path or ".." in relative_path.replace("\\", "/"):
        raise FileUploadError("Geçersiz dosya yolu.")

    normalized = relative_path.replace("\\", "/").lstrip("/")
    if not normalized.startswith("uploads/metadata/"):
        raise FileUploadError("Yalnızca metadata upload dizinindeki dosyalar düzenlenebilir.")

    media_root = Path(settings.MEDIA_ROOT).resolve()
    full_path = (media_root / normalized).resolve()
    try:
        full_path.relative_to(media_root)
    except ValueError as e:
        raise FileUploadError("Geçersiz dosya yolu.") from e
    if not full_path.is_file():
        raise FileUploadError("Kaynak dosya bulunamadı.")

    return full_path


def _can_write_exif(absolute_path: str) -> bool:
    return Path(absolute_path).suffix.lower() in ImageMetadataWriteService.JPEG_EXTENSIONS


def _media_url_for(relative_path: str) -> str:
    base = settings.MEDIA_URL.rstrip("/")
    return f"{base}/{relative_path.replace(chr(92), '/')}"


def _attach_image_analiz(context: dict) -> None:
    metadata = context.get("metadata")
    file_info = context.get("file")
    if not metadata or metadata.get("error") or not file_info:
        return
    target = file_info.get("original_name") or file_info.get("stored_name") or "image"
    report = {
        "file": file_info,
        "metadata": metadata,
    }
    if context.get("edited_file"):
        report["edited_file"] = context["edited_file"]
    attach_analiz(context, module="image_osint", target=target, report=report)
