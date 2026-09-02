# Sherlock + Maigret sonuç birleştirme.
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


class UsernameMergeService:
    @classmethod
    def merge(
        cls,
        *,
        sherlock: dict[str, Any] | None = None,
        maigret: dict[str, Any] | None = None,
        variant_scans: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        entries: list[dict[str, Any]] = []

        for bundle in (sherlock, maigret):
            if bundle and bundle.get("all_results"):
                entries.extend(bundle["all_results"])

        for scan in variant_scans or []:
            if scan.get("found"):
                for item in scan["found"]:
                    entries.append({**item, "from_variant": True})

        merged_found = cls._merge_found(entries)
        not_found = cls._collect_status(entries, "not_found", exclude_urls={m["url"] for m in merged_found if m.get("url")})
        unclear = cls._collect_status(entries, "unclear", exclude_urls={m["url"] for m in merged_found if m.get("url")})

        by_category: dict[str, int] = {}
        for item in merged_found:
            cat = item.get("category") or "other"
            by_category[cat] = by_category.get(cat, 0) + 1

        total_queried = sum(
            b.get("summary", {}).get("queried_count", 0)
            for b in (sherlock, maigret)
            if b
        )

        return {
            "found": merged_found,
            "not_found": not_found,
            "unclear": unclear,
            "by_category": by_category,
            "summary": {
                "queried_count": total_queried,
                "found_count": len(merged_found),
                "not_found_count": len(not_found),
                "unclear_count": len(unclear),
                "unique_platforms_found": len({m["platform"] for m in merged_found}),
            },
        }

    @classmethod
    def _merge_found(cls, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        by_key: dict[str, dict[str, Any]] = {}
        for entry in entries:
            if entry.get("status") != "found":
                continue
            url = cls._normalize_url(entry.get("url") or "")
            key = url or f"{entry.get('platform', '').lower()}:{entry.get('domain', '')}"
            if not key:
                continue

            if key not in by_key:
                by_key[key] = {
                    "platform": entry.get("platform", ""),
                    "domain": entry.get("domain", ""),
                    "url": entry.get("url", ""),
                    "category": entry.get("category", "other"),
                    "sources": [entry.get("source", "unknown")],
                    "confidence": entry.get("confidence"),
                    "matched_username": entry.get("matched_username"),
                    "tags": list(entry.get("tags") or []),
                    "metadata": dict(entry.get("metadata") or {}),
                    "from_variant": entry.get("from_variant", False),
                    "status": "found",
                    "status_label": "Hesap var",
                }
                continue

            existing = by_key[key]
            source = entry.get("source", "unknown")
            if source not in existing["sources"]:
                existing["sources"].append(source)
            if entry.get("confidence") and (
                existing.get("confidence") is None or entry["confidence"] > existing["confidence"]
            ):
                existing["confidence"] = entry["confidence"]
            if entry.get("from_variant"):
                existing["from_variant"] = True
            for tag in entry.get("tags") or []:
                if tag not in existing["tags"]:
                    existing["tags"].append(tag)

        results = list(by_key.values())
        for item in results:
            item["source_label"] = cls._source_label(item["sources"])
        results.sort(key=lambda x: (x.get("category", ""), x.get("platform", "").lower()))
        return results

    @staticmethod
    def _collect_status(
        entries: list[dict[str, Any]],
        status: str,
        *,
        exclude_urls: set[str],
    ) -> list[dict[str, Any]]:
        seen: set[str] = set()
        output: list[dict[str, Any]] = []
        for entry in entries:
            if entry.get("status") != status:
                continue
            url = entry.get("url") or ""
            if url in exclude_urls:
                continue
            key = f"{entry.get('platform')}:{url}"
            if key in seen:
                continue
            seen.add(key)
            output.append({
                "platform": entry.get("platform", ""),
                "domain": entry.get("domain", ""),
                "url": url,
                "source": entry.get("source", ""),
                "category": entry.get("category", "other"),
                "status": status,
                "status_label": entry.get("status_label", status),
            })
        output.sort(key=lambda x: x.get("platform", "").lower())
        return output

    @staticmethod
    def _normalize_url(url: str) -> str:
        if not url:
            return ""
        parsed = urlparse(url.strip().rstrip("/"))
        path = parsed.path.rstrip("/")
        return f"{parsed.netloc.replace('www.', '')}{path}".lower()

    @staticmethod
    def _source_label(sources: list[str]) -> str:
        has_s = "sherlock" in sources
        has_m = "maigret" in sources
        if has_s and has_m:
            return "both"
        if has_m:
            return "maigret"
        if has_s:
            return "sherlock"
        return sources[0] if sources else "unknown"
