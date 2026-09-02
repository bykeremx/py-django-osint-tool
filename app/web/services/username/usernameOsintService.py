# Username OSINT orchestrator.
from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from app.web.services.username.githubProfileService import GithubProfileService
from app.web.services.username.maigretScanService import MaigretScanService
from app.web.services.username.sherlockScanService import SherlockScanService
from app.web.services.username.usernameMergeService import UsernameMergeService
from app.web.services.username.usernameRiskService import UsernameRiskService
from app.web.services.username.usernameValidationService import UsernameValidationService

SCAN_MODES = {"quick", "standard", "deep"}


class UsernameOsintService:
    @classmethod
    def analyze(
        cls,
        username: str,
        *,
        scan_mode: str = "standard",
        generate_variants: bool = False,
    ) -> dict[str, Any]:
        started = time.time()
        mode = scan_mode if scan_mode in SCAN_MODES else "standard"

        validation = UsernameValidationService.analyze(username, generate_variants=generate_variants)
        if not validation.get("valid"):
            return {
                "error": validation.get("error"),
                "username": username,
                "scan_mode": mode,
                "validation": validation,
                "elapsed_seconds": round(time.time() - started, 2),
            }

        normalized = validation["normalized"]
        sherlock_result: dict[str, Any] | None = None
        maigret_result: dict[str, Any] | None = None
        github_result: dict[str, Any] | None = None
        variant_scans: list[dict[str, Any]] = []

        tasks: dict[str, Any] = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            tasks["sherlock"] = pool.submit(SherlockScanService.scan, normalized)
            if mode in ("standard", "deep"):
                tasks["maigret"] = pool.submit(MaigretScanService.scan, normalized, mode=mode)
                tasks["github"] = pool.submit(GithubProfileService.lookup, normalized)

            if generate_variants and validation.get("variants"):
                for variant in validation["variants"]:
                    key = f"variant_{variant}"
                    tasks[key] = pool.submit(SherlockScanService.scan, variant)

            for key, future in tasks.items():
                result = future.result()
                if key == "sherlock":
                    sherlock_result = result
                elif key == "maigret":
                    maigret_result = result
                elif key == "github":
                    github_result = result
                elif key.startswith("variant_"):
                    variant_scans.append(result)

        merged = UsernameMergeService.merge(
            sherlock=sherlock_result,
            maigret=maigret_result,
            variant_scans=variant_scans,
        )
        risk = UsernameRiskService.analyze(
            username=normalized,
            merged=merged,
            github=github_result,
            validation=validation,
        )

        engines = ["sherlock"]
        if mode in ("standard", "deep"):
            engines.extend(["maigret", "github"])

        return {
            "error": None,
            "username": normalized,
            "scan_mode": mode,
            "scan_mode_label": cls._mode_label(mode),
            "engines": engines,
            "validation": validation,
            "sherlock": sherlock_result,
            "maigret": maigret_result,
            "github": github_result,
            "variant_scans": variant_scans,
            "merged": merged,
            "risk": risk,
            "elapsed_seconds": round(time.time() - started, 2),
        }

    @staticmethod
    def _mode_label(mode: str) -> str:
        labels = {
            "quick": "Hızlı (Sherlock)",
            "standard": "Standart (Sherlock + Maigret 500 + GitHub)",
            "deep": "Derin (Sherlock + Maigret tüm DB + GitHub)",
        }
        return labels.get(mode, mode)
