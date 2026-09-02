from django.shortcuts import render

from app.web.services.common.scanJobService import dispatch_scan
from app.web.tasks.scan_tasks import run_email_osint


def index(request):
    context: dict = {}

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        context["email"] = email
        if not email:
            context["error"] = "Lütfen bir e-posta adresi girin."
            return render(request, "pages/email_osint.html", context)

    return dispatch_scan(
        request,
        context,
        template_name="pages/email_osint.html",
        task_fn=run_email_osint,
        task_args=((request.POST.get("email") or "").strip(),) if request.method == "POST" else (),
        module="email_osint",
        target=(request.POST.get("email") or "").strip() if request.method == "POST" else "",
    )
