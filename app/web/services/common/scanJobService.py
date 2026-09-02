"""Tarama isteklerini arka plan kuyruğuna yönlendirme ve sonuç çözümleme."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect, render
from django_rq import get_queue
from rq.command import send_stop_job_command
from rq.exceptions import InvalidJobOperation
from rq.job import Job

SESSION_KEY = "scan_jobs"
MAX_SESSION_JOBS = 30

MODULE_LABELS = {
    "dns_scan": "DNS recon",
    "network_intel": "Network intel",
    "email_osint": "Email OSINT",
    "username_osint": "Username OSINT",
    "nmap_scan": "Nmap scan",
}


def queue_enabled() -> bool:
    return bool(getattr(settings, "SCAN_USE_BACKGROUND_QUEUE", True))


def enqueue_scan(task_fn: Callable[..., dict[str, Any]], *args, **kwargs):
    queue = get_queue("default")
    return queue.enqueue(
        task_fn,
        *args,
        **kwargs,
        result_ttl=86400,
        job_timeout=3600,
        failure_ttl=86400,
    )


def register_scan_job(
    request,
    *,
    job_id: str,
    module: str,
    target: str,
    return_path: str,
) -> None:
    jobs = list(request.session.get(SESSION_KEY, []))
    jobs = [job for job in jobs if job.get("job_id") != job_id]
    jobs.insert(
        0,
        {
            "job_id": job_id,
            "module": module,
            "module_label": MODULE_LABELS.get(module, module),
            "target": target,
            "return_path": return_path,
        },
    )
    request.session[SESSION_KEY] = jobs[:MAX_SESSION_JOBS]
    request.session.modified = True


def resolve_job_status(job_id: str, session_job: dict[str, Any] | None = None) -> str:
    if session_job and session_job.get("cancelled"):
        return "cancelled"
    payload = fetch_job_payload(job_id)
    if payload is None:
        return "missing"
    if payload.get("cancelled"):
        return "cancelled"
    if payload.get("pending"):
        return "pending"
    if payload.get("error"):
        return "failed"
    return "finished"


def get_scan_jobs_with_status(request) -> list[dict[str, Any]]:
    jobs = list(request.session.get(SESSION_KEY, []))
    enriched: list[dict[str, Any]] = []
    for job in jobs:
        status = resolve_job_status(job["job_id"], session_job=job)
        payload = fetch_job_payload(job["job_id"])
        if job.get("cancelled"):
            status = "cancelled"
        enriched.append(
            {
                **job,
                "status": status,
                "error": (payload or {}).get("error") if status != "cancelled" else "Tarama iptal edildi.",
                "result_url": f"{job['return_path']}?job_id={job['job_id']}",
            }
        )
    return enriched


def fetch_job_payload(job_id: str) -> dict[str, Any] | None:
    try:
        job = Job.fetch(job_id, connection=get_queue("default").connection)
    except Exception:
        return None

    if job.is_failed:
        exc = job.exc_info or "Tarama başarısız."
        return {"pending": False, "error": str(exc)}

    if job.is_canceled or job.is_stopped:
        return {
            "pending": False,
            "error": "Tarama iptal edildi.",
            "cancelled": True,
        }

    if not job.is_finished:
        return {"pending": True}

    result = job.result
    if not isinstance(result, dict):
        return {"pending": False, "error": "Geçersiz tarama sonucu."}
    if result.get("error") == "Tarama iptal edildi.":
        result["pending"] = False
        result["cancelled"] = True
        return result
    result["pending"] = False
    return result


def _job_in_session(request, job_id: str) -> bool:
    jobs = request.session.get(SESSION_KEY, [])
    return any(job.get("job_id") == job_id for job in jobs)


def _mark_job_cancelled_in_session(request, job_id: str) -> None:
    jobs = list(request.session.get(SESSION_KEY, []))
    for job in jobs:
        if job.get("job_id") == job_id:
            job["cancelled"] = True
    request.session[SESSION_KEY] = jobs
    request.session.modified = True


def cancel_scan_job(request, job_id: str) -> dict[str, Any]:
    if not _job_in_session(request, job_id):
        return {"ok": False, "error": "Bu iş oturumunuza ait değil."}

    connection = get_queue("default").connection
    try:
        job = Job.fetch(job_id, connection=connection)
    except Exception:
        _mark_job_cancelled_in_session(request, job_id)
        return {"ok": True, "message": "Tarama iptal edildi."}

    if job.is_finished:
        return {"ok": False, "error": "Tamamlanmış iş iptal edilemez."}

    _mark_job_cancelled_in_session(request, job_id)

    if job.is_canceled or job.is_stopped:
        return {"ok": True, "message": "Tarama iptal edildi."}

    try:
        if job.is_started:
            try:
                send_stop_job_command(connection, job_id)
            except InvalidJobOperation:
                pass
        job = Job.fetch(job_id, connection=connection)
        if not job.is_canceled and not job.is_stopped and not job.is_finished:
            job.cancel()
    except InvalidJobOperation:
        pass
    except Exception:
        pass

    return {"ok": True, "message": "Tarama iptal edildi."}


def cancel_all_pending_scan_jobs(request) -> dict[str, Any]:
    jobs = get_scan_jobs_with_status(request)
    cancelled = 0
    errors: list[str] = []
    for job in jobs:
        if job["status"] != "pending":
            continue
        result = cancel_scan_job(request, job["job_id"])
        if result.get("ok"):
            cancelled += 1
        elif result.get("error"):
            errors.append(result["error"])
    return {"ok": True, "cancelled": cancelled, "errors": errors}


def apply_scan_payload(context: dict[str, Any], payload: dict[str, Any]) -> None:
    from app.web.views.analiz.helpers import attach_analiz

    context.update(payload.get("context_updates") or {})
    if payload.get("error"):
        context["error"] = payload["error"]
    analiz = payload.get("analiz")
    if analiz:
        attach_analiz(
            context,
            module=analiz["module"],
            target=analiz["target"],
            report=analiz.get("report"),
        )


def dispatch_scan(
    request,
    context: dict[str, Any],
    *,
    template_name: str,
    task_fn: Callable[..., dict[str, Any]],
    task_args: tuple = (),
    task_kwargs: dict[str, Any] | None = None,
    module: str = "",
    target: str = "",
):
    task_kwargs = task_kwargs or {}
    job_id = request.GET.get("job_id")

    if job_id:
        session_jobs = request.session.get(SESSION_KEY, [])
        session_job = next(
            (job for job in session_jobs if job.get("job_id") == job_id),
            None,
        )
        if session_job and session_job.get("cancelled"):
            context["error"] = "Tarama iptal edildi."
            return render(request, template_name, context)

        payload = fetch_job_payload(job_id)
        if payload is None:
            context["error"] = "Geçersiz veya süresi dolmuş tarama işi."
            return render(request, template_name, context)
        if payload.get("cancelled"):
            context["error"] = payload.get("error", "Tarama iptal edildi.")
            return render(request, template_name, context)
        if payload.get("pending"):
            context["scan_job_id"] = job_id
            context["scan_job_banner"] = True
            return render(request, template_name, context)
        apply_scan_payload(context, payload)
        return render(request, template_name, context)

    if request.method != "POST":
        return render(request, template_name, context)

    if queue_enabled():
        try:
            job = enqueue_scan(task_fn, *task_args, **task_kwargs)
            register_scan_job(
                request,
                job_id=job.id,
                module=module,
                target=target,
                return_path=request.path,
            )
            label = MODULE_LABELS.get(module, "Tarama")
            messages.success(
                request,
                f"「{target}」 {label} kuyruğa alındı. Diğer modüllere devam edebilirsiniz.",
            )
            return redirect("dashboard")
        except Exception as exc:
            messages.warning(
                request,
                f"Kuyruk kullanılamadı ({exc}). Tarama bu sayfada senkron çalışacak — bitene kadar bekleyin.",
            )

    payload = task_fn(*task_args, **task_kwargs)
    apply_scan_payload(context, payload)
    return render(request, template_name, context)
