from app.web.services.common.scanJobService import get_scan_jobs_with_status, queue_enabled


def scan_queue(request):
    enabled = queue_enabled()
    pending = 0
    if enabled and hasattr(request, "session"):
        jobs = get_scan_jobs_with_status(request)
        pending = sum(1 for job in jobs if job.get("status") == "pending")
    return {
        "scan_queue_enabled": enabled,
        "scan_queue_pending": pending,
    }
