from django.shortcuts import render

from app.web.services.common.scanJobService import dispatch_scan
from app.web.tasks.scan_tasks import run_username_osint


def index(request):
    context: dict = {}

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        scan_mode = (request.POST.get("scan_mode") or "standard").strip()
        generate_variants = request.POST.get("generate_variants") == "on"
        context["username"] = username
        context["scan_mode"] = scan_mode
        context["generate_variants"] = generate_variants
        if not username:
            context["error"] = "Lütfen bir kullanıcı adı girin."
            return render(request, "pages/username_osint.html", context)

    if request.method == "POST":
        task_kwargs = {
            "username": (request.POST.get("username") or "").strip(),
            "scan_mode": (request.POST.get("scan_mode") or "standard").strip(),
            "generate_variants": request.POST.get("generate_variants") == "on",
        }
    else:
        task_kwargs = {}

    return dispatch_scan(
        request,
        context,
        template_name="pages/username_osint.html",
        task_fn=run_username_osint,
        task_kwargs=task_kwargs if request.method == "POST" else None,
        module="username_osint",
        target=(request.POST.get("username") or "").strip() if request.method == "POST" else "",
    )
