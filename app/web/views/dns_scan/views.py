from django.shortcuts import render

from app.web.services.common.scanJobService import dispatch_scan
from app.web.tasks.scan_tasks import run_dns_scan


def index(request):
    context: dict = {}

    if request.method == "POST":
        domain = (request.POST.get("domain") or "").strip()
        context["domain"] = domain
        if not domain:
            context["error"] = "Lütfen bir domain girin."
            return render(request, "pages/dns_scan.html", context)

    return dispatch_scan(
        request,
        context,
        template_name="pages/dns_scan.html",
        task_fn=run_dns_scan,
        task_args=((request.POST.get("domain") or "").strip(),) if request.method == "POST" else (),
        module="dns_scan",
        target=(request.POST.get("domain") or "").strip() if request.method == "POST" else "",
    )
