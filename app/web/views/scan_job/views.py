from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST

from app.web.services.common.scanJobService import (
    cancel_all_pending_scan_jobs,
    cancel_scan_job,
    fetch_job_payload,
    get_scan_jobs_with_status,
)


@require_GET
def status(request, job_id: str):
    payload = fetch_job_payload(job_id)
    if payload is None:
        return JsonResponse({"status": "missing", "error": "İş bulunamadı."}, status=404)
    if payload.get("cancelled"):
        return JsonResponse({"status": "cancelled", "error": payload.get("error")})
    if payload.get("pending"):
        return JsonResponse({"status": "pending"})
    if payload.get("error"):
        return JsonResponse({"status": "failed", "error": payload["error"]})
    return JsonResponse({"status": "finished"})


@ensure_csrf_cookie
@require_GET
def active_jobs(request):
    jobs = get_scan_jobs_with_status(request)
    pending_count = sum(1 for job in jobs if job["status"] == "pending")
    return JsonResponse({"jobs": jobs, "pending_count": pending_count})


@require_POST
def cancel_job(request, job_id: str):
    result = cancel_scan_job(request, job_id)
    status_code = 200 if result.get("ok") else 400
    return JsonResponse(result, status=status_code)


@require_POST
def cancel_all_jobs(request):
    result = cancel_all_pending_scan_jobs(request)
    return JsonResponse(result)
