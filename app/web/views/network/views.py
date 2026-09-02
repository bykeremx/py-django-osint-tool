from django.shortcuts import render

from app.web.services.common.scanJobService import dispatch_scan
from app.web.tasks.scan_tasks import run_network_intel


def index(request):
    context: dict = {}

    if request.method == "POST":
        domain = (request.POST.get("domain") or "").strip()
        context["domain"] = domain
        if not domain:
            context["error"] = "Lütfen bir domain veya IP girin."
            return render(request, "pages/network_intel.html", context)

    return dispatch_scan(
        request,
        context,
        template_name="pages/network_intel.html",
        task_fn=run_network_intel,
        task_args=((request.POST.get("domain") or "").strip(),) if request.method == "POST" else (),
        module="network_intel",
        target=(request.POST.get("domain") or "").strip() if request.method == "POST" else "",
    )
