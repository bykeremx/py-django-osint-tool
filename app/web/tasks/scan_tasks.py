"""Arka plan tarama görevleri (django-rq worker tarafından çalıştırılır)."""
from __future__ import annotations

from typing import Any


class ScanCancelled(Exception):
    """Kuyruk iptali — worker görevi sonlandırır."""


def _ensure_not_cancelled() -> None:
    from rq.job import get_current_job

    job = get_current_job()
    if job and (job.is_canceled or job.is_stopped):
        raise ScanCancelled("Tarama iptal edildi.")


def _payload(*, context_updates: dict[str, Any], analiz: dict[str, Any] | None = None, error: str | None = None) -> dict[str, Any]:    return {
        "context_updates": context_updates,
        "analiz": analiz,
        "error": error,
    }


def run_dns_scan(domain: str) -> dict[str, Any]:
    from app.web.services.dns.dnsServices import DnsServices

    try:
        _ensure_not_cancelled()
        dns_scan = DnsServices.dns_scan_service(domain)
        _ensure_not_cancelled()
        return _payload(
            context_updates={"domain": domain, "dns_scan": dns_scan},
            analiz={"module": "dns_scan", "target": domain, "report": dns_scan},
        )
    except ScanCancelled:
        return _payload(context_updates={"domain": domain}, error="Tarama iptal edildi.")
    except Exception as e:
        return _payload(context_updates={"domain": domain}, error=str(e))

def run_network_intel(domain: str) -> dict[str, Any]:
    from app.web.services.network.NetworkIntelService import NetworkIntelService

    try:
        _ensure_not_cancelled()
        intel = NetworkIntelService.analyze(domain)
        _ensure_not_cancelled()
        return _payload(
            context_updates={"domain": domain, "intel": intel},
            analiz={"module": "network_intel", "target": domain, "report": intel},
        )
    except ScanCancelled:
        return _payload(context_updates={"domain": domain}, error="Tarama iptal edildi.")
    except Exception as e:
        return _payload(context_updates={"domain": domain}, error=str(e))

def run_email_osint(email: str) -> dict[str, Any]:
    from app.web.services.email.emailOsintService import EmailOsintService

    try:
        _ensure_not_cancelled()
        result = EmailOsintService.analyze(email)
        _ensure_not_cancelled()
        analiz = None
        if not result.get("error"):
            analiz = {"module": "email_osint", "target": email, "report": result}
        return _payload(
            context_updates={"email": email, "result": result},
            analiz=analiz,
            error=result.get("error"),
        )
    except ScanCancelled:
        return _payload(context_updates={"email": email}, error="Tarama iptal edildi.")
    except Exception as e:
        return _payload(context_updates={"email": email}, error=str(e))

def run_username_osint(username: str, scan_mode: str, generate_variants: bool) -> dict[str, Any]:
    from app.web.services.username.usernameOsintService import UsernameOsintService

    try:
        _ensure_not_cancelled()
        result = UsernameOsintService.analyze(
            username,
            scan_mode=scan_mode,
            generate_variants=generate_variants,
        )
        _ensure_not_cancelled()
        analiz = None
        if not result.get("error"):
            analiz = {"module": "username_osint", "target": username, "report": result}
        return _payload(
            context_updates={
                "username": username,
                "scan_mode": scan_mode,
                "generate_variants": generate_variants,
                "result": result,
            },
            analiz=analiz,
            error=result.get("error"),
        )
    except ScanCancelled:
        return _payload(
            context_updates={
                "username": username,
                "scan_mode": scan_mode,
                "generate_variants": generate_variants,
            },
            error="Tarama iptal edildi.",
        )
    except Exception as e:
        return _payload(
            context_updates={
                "username": username,
                "scan_mode": scan_mode,
                "generate_variants": generate_variants,
            },
            error=str(e),
        )

def run_nmap_scan(target: str, scan_mode: str) -> dict[str, Any]:
    from app.web.services.nmap.nmapScanService import NmapScanService

    try:
        _ensure_not_cancelled()
        result = NmapScanService.scan(target, mode=scan_mode)
        _ensure_not_cancelled()
        analiz = None
        if not result.get("error"):
            analiz = {"module": "nmap_scan", "target": target, "report": result}
        return _payload(
            context_updates={"target": target, "scan_mode": scan_mode, "scan": result},
            analiz=analiz,
            error=result.get("error"),
        )
    except ScanCancelled:
        return _payload(context_updates={"target": target, "scan_mode": scan_mode}, error="Tarama iptal edildi.")
    except Exception as e:
        return _payload(context_updates={"target": target, "scan_mode": scan_mode}, error=str(e))