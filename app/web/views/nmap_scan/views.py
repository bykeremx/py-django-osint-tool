from django.shortcuts import render

from app.web.services.common.scanJobService import dispatch_scan
from app.web.tasks.scan_tasks import run_nmap_scan


def index(request):
    context: dict = {}

    if request.method == "POST":
        target = (request.POST.get("target") or "").strip()
        scan_mode = (request.POST.get("scan_mode") or "standard").strip()
        context["target"] = target
        context["scan_mode"] = scan_mode
        if not target:
            context["error"] = "Lütfen bir IP veya hostname girin."
            return render(request, "pages/nmap_scan.html", context)

    if request.method == "POST":
        task_kwargs = {
            "target": (request.POST.get("target") or "").strip(),
            "scan_mode": (request.POST.get("scan_mode") or "standard").strip(),
        }
    else:
        task_kwargs = {}

    return dispatch_scan(
        request,
        context,
        template_name="pages/nmap_scan.html",
        task_fn=run_nmap_scan,
        task_kwargs=task_kwargs if request.method == "POST" else None,
        module="nmap_scan",
        target=(request.POST.get("target") or "").strip() if request.method == "POST" else "",
    )
