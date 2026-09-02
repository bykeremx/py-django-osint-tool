# Kullanıcı adı doğrulama ve varyant üretimi.
from __future__ import annotations

import re
from typing import Any

USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]{3,32}$")
MAX_VARIANTS = 5


class UsernameValidationService:
    @classmethod
    def analyze(cls, username: str, *, generate_variants: bool = False) -> dict[str, Any]:
        raw = (username or "").strip()
        if not raw:
            return {"valid": False, "error": "Kullanıcı adı boş."}

        if " " in raw:
            return {"valid": False, "error": "Kullanıcı adında boşluk olamaz."}

        if not USERNAME_PATTERN.fullmatch(raw):
            return {
                "valid": False,
                "error": "Geçersiz format. İzin verilen: harf, rakam, nokta, alt çizgi, tire (3–32 karakter).",
            }

        normalized = raw.lower()
        variants = cls._generate_variants(normalized) if generate_variants else []

        return {
            "valid": True,
            "error": None,
            "raw": raw,
            "normalized": normalized,
            "length": len(raw),
            "has_dot": "." in normalized,
            "has_underscore": "_" in normalized,
            "has_hyphen": "-" in normalized,
            "has_digit": any(ch.isdigit() for ch in normalized),
            "variants": variants,
            "hints": cls._hints(normalized),
        }

    @staticmethod
    def _generate_variants(normalized: str) -> list[str]:
        candidates: set[str] = set()
        candidates.add(normalized.replace("_", ""))
        candidates.add(normalized.replace(".", ""))
        candidates.add(normalized.replace("-", ""))
        candidates.add(normalized.capitalize())
        no_trailing_digits = re.sub(r"\d+$", "", normalized)
        if no_trailing_digits and len(no_trailing_digits) >= 3:
            candidates.add(no_trailing_digits)
        if normalized.islower():
            candidates.add(normalized.upper())

        candidates.discard(normalized)
        return sorted(c for c in candidates if USERNAME_PATTERN.fullmatch(c))[:MAX_VARIANTS]

    @staticmethod
    def _hints(normalized: str) -> list[str]:
        hints: list[str] = []
        if normalized.isdigit():
            hints.append("yalnızca-rakam")
        if len(normalized) <= 4:
            hints.append("kısa-ad")
        if normalized.count("_") + normalized.count(".") >= 2:
            hints.append("ayırıcılı")
        return hints
