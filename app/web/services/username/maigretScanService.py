# Maigret — geniş kapsamlı username / profil keşfi.
from __future__ import annotations

import asyncio
import logging
import sys
import threading
from typing import Any
from urllib.parse import urlparse

from maigret.checking import maigret as maigret_search
from maigret.db_updater import BUNDLED_DB_PATH
from maigret.result import MaigretCheckStatus
from maigret.sites import MaigretDatabase

ADULT_EXCLUDED_TAGS = ["porn", "adult", "xxx", "nsfw"]
TOP_STANDARD_SITES = 500

_maigret_db: MaigretDatabase | None = None
_maigret_standard_sites: dict[str, Any] | None = None
_maigret_lock = threading.Lock()


def _get_maigret_db() -> MaigretDatabase:
    global _maigret_db
    if _maigret_db is not None:
        return _maigret_db
    with _maigret_lock:
        if _maigret_db is None:
            _maigret_db = MaigretDatabase().load_from_path(BUNDLED_DB_PATH)
    return _maigret_db


def _get_maigret_site_dict(*, top: int) -> dict[str, Any]:
    global _maigret_standard_sites
    if top != sys.maxsize:
        if _maigret_standard_sites is not None:
            return _maigret_standard_sites
        with _maigret_lock:
            if _maigret_standard_sites is None:
                _maigret_standard_sites = _get_maigret_db().ranked_sites_dict(
                    top=TOP_STANDARD_SITES,
                    excluded_tags=ADULT_EXCLUDED_TAGS,
                    disabled=False,
                )
        return _maigret_standard_sites
    return _get_maigret_db().ranked_sites_dict(
        top=top,
        excluded_tags=ADULT_EXCLUDED_TAGS,
        disabled=False,
    )


class MaigretScanService:
    DEFAULT_TIMEOUT = 15
    TOP_STANDARD = TOP_STANDARD_SITES
    MAX_CONNECTIONS = 40

    @classmethod
    def scan(cls, username: str, *, mode: str = "standard", timeout: int | None = None) -> dict[str, Any]:
        timeout = timeout or cls.DEFAULT_TIMEOUT
        top = cls.TOP_STANDARD if mode != "deep" else sys.maxsize
        try:
            raw = asyncio.run(cls._run_scan(username, top=top, timeout=timeout))
        except Exception as e:
            return cls._empty_result(username, error=str(e))
        return cls._format_results(username, raw)

    @classmethod
    async def _run_scan(cls, username: str, *, top: int, timeout: int) -> dict[str, Any]:
        logger = logging.getLogger("maigret.django")
        logger.setLevel(logging.ERROR)
        site_dict = _get_maigret_site_dict(top=top)
        return await maigret_search(
            username=username,
            site_dict=site_dict,
            logger=logger,
            timeout=timeout,
            is_parsing_enabled=False,
            no_progressbar=True,
            max_connections=cls.MAX_CONNECTIONS,
        )

    @classmethod
    def _format_results(cls, username: str, raw: dict[str, Any]) -> dict[str, Any]:
        found: list[dict[str, Any]] = []
        not_found: list[dict[str, Any]] = []
        unclear: list[dict[str, Any]] = []

        for platform, data in raw.items():
            status_obj = data.get("status")
            url_user = (data.get("url_user") or "").strip()
            url_main = data.get("url_main") or ""
            domain = cls._domain_from_url(url_user or url_main)
            tags = []
            if status_obj and getattr(status_obj, "tags", None):
                tags = list(status_obj.tags)

            entry = {
                "platform": platform,
                "domain": domain,
                "url": url_user,
                "url_main": url_main,
                "http_status": data.get("http_status"),
                "matched_username": username,
                "source": "maigret",
                "confidence": cls._confidence(data, status_obj),
                "category": cls._category_from_tags(tags, platform, domain),
                "tags": tags,
                "metadata": {
                    "ids_data": getattr(status_obj, "ids_data", None) or data.get("ids_data") or {},
                    "is_similar": data.get("is_similar", False),
                },
            }

            if not status_obj:
                unclear.append({**entry, "status": "unclear", "status_label": "Belirsiz"})
                continue

            status = status_obj.status
            if status == MaigretCheckStatus.CLAIMED:
                found.append({**entry, "status": "found", "status_label": "Hesap var"})
            elif status in (MaigretCheckStatus.AVAILABLE, MaigretCheckStatus.ILLEGAL):
                not_found.append({**entry, "status": "not_found", "status_label": "Hesap yok / geçersiz"})
            else:
                unclear.append({**entry, "status": "unclear", "status_label": "Belirsiz / hata"})

        total = len(raw)
        return {
            "error": None,
            "engine": "maigret",
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
    def _confidence(data: dict, status_obj) -> int | None:
        if not status_obj or status_obj.status != MaigretCheckStatus.CLAIMED:
            return None
        if data.get("is_similar"):
            return 70
        return 92

    @staticmethod
    def _empty_result(username: str, error: str) -> dict[str, Any]:
        return {
            "error": error,
            "engine": "maigret",
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
    def _category_from_tags(tags: list, platform: str, domain: str) -> str:
        lowered = {t.lower() for t in tags}
        if lowered.intersection({"coding", "dev", "tech"}):
            return "coding"
        if lowered.intersection({"social", "networking"}):
            return "social"
        if lowered.intersection({"forum", "community"}):
            return "forum"
        if lowered.intersection({"gaming", "games"}):
            return "gaming"
        blob = f"{platform} {domain}".lower()
        if "github" in blob or "gitlab" in blob:
            return "coding"
        if any(x in blob for x in ("reddit", "twitter", "instagram")):
            return "social"
        return "other"
