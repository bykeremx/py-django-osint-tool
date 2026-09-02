# Sherlock — username enumeration.
from __future__ import annotations

import threading
from typing import Any
from urllib.parse import urlparse

from sherlock_project.notify import QueryNotify
from sherlock_project.result import QueryStatus
from sherlock_project.sherlock import sherlock
from sherlock_project.sites import SitesInformation

_sherlock_site_data: dict[str, Any] | None = None
_sherlock_lock = threading.Lock()
EXCLUDE_NSFW = True


def _get_sherlock_site_data() -> dict[str, Any]:
    global _sherlock_site_data
    if _sherlock_site_data is not None:
        return _sherlock_site_data
    with _sherlock_lock:
        if _sherlock_site_data is None:
            site_info = SitesInformation()
            if EXCLUDE_NSFW:
                site_info.remove_nsfw_sites()
            _sherlock_site_data = {
                name: site.information for name, site in site_info.sites.items()
            }
    return _sherlock_site_data


class _SilentNotify(QueryNotify):
    def start(self, message=None) -> None:
        pass

    def update(self, result) -> None:
        pass

    def finish(self, message=None) -> None:
        pass


class SherlockScanService:
    DEFAULT_TIMEOUT = 12
    EXCLUDE_NSFW = EXCLUDE_NSFW

    @classmethod
    def scan(cls, username: str, *, timeout: int | None = None) -> dict[str, Any]:
        timeout = timeout or cls.DEFAULT_TIMEOUT
        try:
            site_data = _get_sherlock_site_data()
            raw = sherlock(username, site_data, _SilentNotify(), timeout=timeout)
        except Exception as e:
            return cls._empty_result(username, error=str(e))

        return cls._format_results(username, raw)

    @classmethod
    def _format_results(cls, username: str, raw: dict[str, Any]) -> dict[str, Any]:
        found: list[dict[str, Any]] = []
        not_found: list[dict[str, Any]] = []
        unclear: list[dict[str, Any]] = []

        for platform, data in raw.items():
            status_obj = data.get("status")
            url_user = (data.get("url_user") or "").strip()
            domain = cls._domain_from_url(url_user or data.get("url_main", ""))
            entry = {
                "platform": platform,
                "domain": domain,
                "url": url_user,
                "url_main": data.get("url_main", ""),
                "http_status": data.get("http_status"),
                "matched_username": username,
                "source": "sherlock",
                "confidence": None,
                "category": cls._guess_category(platform, domain),
                "tags": [],
                "metadata": {},
            }

            if not status_obj:
                unclear.append({**entry, "status": "unclear", "status_label": "Belirsiz"})
                continue

            status = status_obj.status
            if status == QueryStatus.CLAIMED:
                found.append({**entry, "status": "found", "status_label": "Hesap var"})
            elif status in (QueryStatus.AVAILABLE, QueryStatus.ILLEGAL):
                not_found.append({**entry, "status": "not_found", "status_label": "Hesap yok / geçersiz"})
            else:
                unclear.append({**entry, "status": "unclear", "status_label": "Belirsiz / WAF / hata"})

        total = len(raw)
        return {
            "error": None,
            "engine": "sherlock",
            "username": username,
            "total_checked": total,
            "found": found,
            "not_found": not_found,
            "unclear": unclear,
            "all_results": found + not_found + unclear,
            "summary": {
                "queried_count": total,
                "found_count": len(found),
                "not_found_count": len(not_found),
                "unclear_count": len(unclear),
            },
        }

    @staticmethod
    def _empty_result(username: str, error: str) -> dict[str, Any]:
        return {
            "error": error,
            "engine": "sherlock",
            "username": username,
            "total_checked": 0,
            "found": [],
            "not_found": [],
            "unclear": [],
            "all_results": [],
            "summary": {"queried_count": 0, "found_count": 0, "not_found_count": 0, "unclear_count": 0},
        }

    @staticmethod
    def _domain_from_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url if "://" in url else f"https://{url}")
        return (parsed.netloc or "").replace("www.", "")

    @staticmethod
    def _guess_category(platform: str, domain: str) -> str:
        blob = f"{platform} {domain}".lower()
        if any(x in blob for x in ("github", "gitlab", "bitbucket", "codepen", "replit", "stackoverflow", "dev.to")):
            return "coding"
        if any(x in blob for x in ("reddit", "twitter", "instagram", "facebook", "tiktok", "snapchat", "discord")):
            return "social"
        if any(x in blob for x in ("steam", "xbox", "minecraft", "roblox", "chess")):
            return "gaming"
        if any(x in blob for x in ("forum", "community")):
            return "forum"
        return "other"
