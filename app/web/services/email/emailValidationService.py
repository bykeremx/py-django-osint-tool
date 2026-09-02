# E-posta doğrulama ve parçalama.
from __future__ import annotations

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")

FREE_PROVIDERS = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.co.uk", "hotmail.com",
    "outlook.com", "live.com", "icloud.com", "me.com", "proton.me", "protonmail.com",
    "yandex.com", "yandex.ru", "mail.ru", "gmx.com", "gmx.de", "aol.com",
    "zoho.com", "tutanota.com", "fastmail.com",
}

ROLE_LOCAL_PARTS = {
    "admin", "administrator", "info", "contact", "support", "help", "sales",
    "billing", "abuse", "postmaster", "webmaster", "noreply", "no-reply",
    "hr", "jobs", "careers", "security", "dev", "ops",
}


class EmailValidationService:
    @classmethod
    def analyze(cls, email: str) -> dict[str, Any]:
        raw = (email or "").strip()
        normalized = raw.lower()

        if not raw:
            return {"valid": False, "error": "E-posta adresi boş."}

        if not EMAIL_PATTERN.fullmatch(raw):
            return {"valid": False, "error": "Geçersiz e-posta formatı."}

        local, _, domain = normalized.partition("@")
        domain = domain.strip(".")

        return {
            "valid": True,
            "error": None,
            "raw": raw,
            "normalized": normalized,
            "local_part": local,
            "domain": domain,
            "provider_type": cls._provider_type(domain),
            "is_role_address": local in ROLE_LOCAL_PARTS,
            "is_free_provider": domain in FREE_PROVIDERS,
            "local_hints": cls._local_hints(local),
        }

    @staticmethod
    def _provider_type(domain: str) -> str:
        if domain in FREE_PROVIDERS:
            return "free"
        if any(domain.endswith(suffix) for suffix in (".edu", ".ac.uk", ".edu.tr")):
            return "education"
        if any(domain.endswith(suffix) for suffix in (".gov", ".gov.tr", ".mil")):
            return "government"
        return "custom"

    @staticmethod
    def _local_hints(local: str) -> list[str]:
        hints: list[str] = []
        if local in ROLE_LOCAL_PARTS:
            hints.append("role-based")
        if local.count(".") >= 2:
            hints.append("dotted-local")
        if "+" in local:
            hints.append("plus-alias")
        if any(ch.isdigit() for ch in local):
            hints.append("contains-digit")
        return hints
