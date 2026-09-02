from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie

from app.web.services.common.scanJobService import get_scan_jobs_with_status
from core.models import Analiz


@ensure_csrf_cookie
def dashboard_view(request):
    recent_analiz = Analiz.objects.all()[:15]
    total_analiz = Analiz.objects.count()
    scan_jobs = get_scan_jobs_with_status(request)
    pending_scans = sum(1 for job in scan_jobs if job["status"] == "pending")
    return render(
        request,
        "pages/dashboard.html",
        {
            "recent_analiz": recent_analiz,
            "total_analiz": total_analiz,
            "scan_jobs": scan_jobs,
            "pending_scans": pending_scans,
        },
    )
