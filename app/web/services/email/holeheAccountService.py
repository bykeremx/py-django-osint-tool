# Hesap varlığı taraması — holehe modülleri.
from __future__ import annotations

from typing import Any

import httpx
import trio
from holehe.core import get_functions, import_submodules, launch_module


class _HoleheArgs:
    nopasswordrecovery = False


class HoleheAccountService:
    DEFAULT_TIMEOUT = 12.0

    @classmethod
    def scan(cls, email: str, *, timeout: float | None = None) -> dict[str, Any]:
        timeout = timeout or cls.DEFAULT_TIMEOUT
        try:
            raw_results = trio.run(cls._run_scan, email, timeout)
        except Exception as e:
            return {
                "error": f"Holehe taraması başarısız: {e}",
                "total_checked": 0,
                "found": [],
                "not_found": [],
                "rate_limited": [],
                "unclear": [],
                "all_results": [],
                "summary": {
                    "queried_count": 0,
                    "found_count": 0,
                    "not_found_count": 0,
                    "unclear_count": 0,
                    "rate_limited_count": 0,
                    "hit_rate": 0,
                },
            }

        return cls._format_results(raw_results)

    @staticmethod
    async def _run_scan(email: str, timeout: float) -> list[dict[str, Any]]:
        modules = import_submodules("holehe.modules")
        websites = get_functions(modules, _HoleheArgs())
        client = httpx.AsyncClient(timeout=timeout)
        out: list[dict[str, Any]] = []

        async with trio.open_nursery() as nursery:
            for website in websites:
                nursery.start_soon(launch_module, website, email, client, out)

        await client.aclose()
        return sorted(out, key=lambda item: item.get("name", ""))

    @classmethod
    def _format_results(cls, raw: list[dict[str, Any]]) -> dict[str, Any]:
        found: list[dict[str, Any]] = []
        not_found: list[dict[str, Any]] = []
        rate_limited: list[dict[str, Any]] = []

        for item in raw:
            entry = {
                "name": item.get("name", ""),
                "domain": item.get("domain", ""),
                "method": item.get("method"),
                "emailrecovery": item.get("emailrecovery"),
                "phone_number": item.get("phoneNumber"),
                "others": item.get("others"),
            }
            if item.get("rateLimit"):
                rate_limited.append(entry)
            elif item.get("exists"):
                found.append(entry)
            else:
                not_found.append(entry)

        total = len(raw)
        return {
            "error": None,
            "total_checked": total,
            "found": found,
            "not_found": not_found,
            "rate_limited": rate_limited,
            "unclear": rate_limited,
            "all_results": cls._with_status(raw),
            "summary": {
                "queried_count": total,
                "found_count": len(found),
                "not_found_count": len(not_found),
                "unclear_count": len(rate_limited),
                "rate_limited_count": len(rate_limited),
                "hit_rate": round(len(found) / total * 100, 1) if total else 0,
            },
        }

    @staticmethod
    def _with_status(raw: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for item in raw:
            if item.get("rateLimit"):
                status = "unclear"
                status_label = "Belirsiz — yanıt alınamadı"
            elif item.get("exists"):
                status = "found"
                status_label = "Hesap var"
            else:
                status = "not_found"
                status_label = "Hesap yok"
            items.append({
                "name": item.get("name", ""),
                "domain": item.get("domain", ""),
                "status": status,
                "status_label": status_label,
                "method": item.get("method"),
                "emailrecovery": item.get("emailrecovery"),
                "phone_number": item.get("phoneNumber"),
                "others": item.get("others"),
            })
        return items
