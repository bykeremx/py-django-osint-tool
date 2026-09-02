import json

from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from app.web.services.common.analizService import AnalizService
from core.models import Analiz


def _parse_body(request) -> dict:
    if request.content_type and "application/json" in request.content_type:
        return json.loads(request.body.decode("utf-8"))
    return {
        "module": request.POST.get("module", ""),
        "target": request.POST.get("target", ""),
        "note": request.POST.get("note", ""),
        "report": json.loads(request.POST.get("report", "{}")),
        "items": json.loads(request.POST.get("items", "[]")),
    }


@require_POST
def kaydet(request):
    try:
        body = _parse_body(request)
        module = (body.get("module") or "").strip()
        target = (body.get("target") or "").strip()
        note = (body.get("note") or "").strip()
        report = body.get("report") or {}
        items = body.get("items") or []

        if not isinstance(items, list):
            items = []

        valid_modules = {c[0] for c in Analiz.MODULE_CHOICES}
        if module not in valid_modules:
            return JsonResponse({"ok": False, "error": "Geçersiz modül."}, status=400)
        if not target:
            return JsonResponse({"ok": False, "error": "Hedef (target) gerekli."}, status=400)

        analiz = AnalizService.save(
            module=module,
            target=target,
            report=report,
            note=note,
            items=items,
        )
        export_data = AnalizService.export_dict(analiz)

        return JsonResponse({
            "ok": True,
            "id": analiz.pk,
            "detail_url": f"/analiz/{analiz.pk}/",
            "download_url": f"/analiz/{analiz.pk}/json/",
            "message": f"Analiz #{analiz.pk} kaydedildi ({analiz.items.count()} madde).",
            "export": export_data,
        })
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "Geçersiz JSON."}, status=400)
    except ValueError as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=400)
    except Exception as e:
        return JsonResponse({"ok": False, "error": str(e)}, status=500)


def download_json(request, pk: int):
    analiz = get_object_or_404(Analiz, pk=pk)
    payload = AnalizService.export_dict(analiz)
    content = json.dumps(payload, ensure_ascii=False, indent=2)
    filename = f"analiz-{analiz.module}-{analiz.target}-{analiz.pk}.json".replace("/", "_")
    response = HttpResponse(content, content_type="application/json; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def detail(request, pk: int):
    analiz = get_object_or_404(Analiz, pk=pk)
    items = analiz.items.all().order_by("id")
    return render(request, "pages/analiz_detail.html", {
        "analiz": analiz,
        "items": items,
        "item_total": items.count(),
    })


@require_POST
def item_ekle(request, pk: int):
    analiz = get_object_or_404(Analiz, pk=pk)
    key = (request.POST.get("key") or "").strip()
    value = (request.POST.get("value") or "").strip()
    try:
        AnalizService.add_item(analiz, key, value)
        messages.success(request, f"Madde eklendi: {key}")
    except ValueError as e:
        messages.error(request, str(e))
    return redirect("analiz_detail", pk=pk)


@require_POST
def item_sil(request, pk: int, item_id: int):
    analiz = get_object_or_404(Analiz, pk=pk)
    if AnalizService.delete_item(item_id, analiz.pk):
        messages.success(request, "Madde silindi.")
    else:
        messages.error(request, "Madde bulunamadı.")
    return redirect("analiz_detail", pk=pk)
