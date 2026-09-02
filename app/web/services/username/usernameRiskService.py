# Username exposure skoru ve bulgular.
from __future__ import annotations

from typing import Any

HIGH_VALUE_PLATFORMS = {
    "github", "twitter", "instagram", "linkedin", "reddit", "facebook",
    "stackoverflow", "gitlab", "youtube", "tiktok", "discord",
}


class UsernameRiskService:
    @classmethod
    def analyze(
        cls,
        *,
        username: str,
        merged: dict[str, Any],
        github: dict[str, Any] | None = None,
        validation: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        found = merged.get("found") or []
        found_count = len(found)
        high_value = [
            f for f in found
            if f.get("platform", "").lower() in HIGH_VALUE_PLATFORMS
            or any(hv in (f.get("domain") or "").lower() for hv in HIGH_VALUE_PLATFORMS)
        ]

        score = min(100, found_count * 4 + len(high_value) * 8)
        if github and github.get("exists"):
            score = min(100, score + 10)
            if github.get("public_email"):
                score = min(100, score + 15)
        if validation and validation.get("has_digit"):
            score = max(0, score - 3)

        if score >= 70:
            level = "high"
            level_label = "Yüksek görünürlük"
        elif score >= 35:
            level = "medium"
            level_label = "Orta görünürlük"
        else:
            level = "low"
            level_label = "Düşük görünürlük"

        findings: list[dict[str, str]] = []
        if found_count:
            findings.append({
                "level": "info",
                "text": f"{found_count} platformda profil / hesap tespit edildi.",
            })
        if high_value:
            findings.append({
                "level": "medium",
                "text": f"{len(high_value)} yüksek değerli platform (GitHub, Reddit, Twitter vb.).",
            })
        if github and github.get("public_email"):
            findings.append({
                "level": "high",
                "text": f"GitHub'da public e-posta: {github['public_email']}",
            })
        if github and github.get("exists") and github.get("bio"):
            findings.append({
                "level": "low",
                "text": f"GitHub bio: {github['bio'][:120]}",
            })
        if merged.get("summary", {}).get("unclear_count", 0) > 50:
            findings.append({
                "level": "low",
                "text": "Çok sayıda belirsiz sonuç — bot koruması veya rate limit etkili olabilir.",
            })
        if not found_count:
            findings.append({
                "level": "info",
                "text": "Kayıtlı profil bulunamadı (veya tüm sonuçlar belirsiz).",
            })

        return {
            "score": score,
            "level": level,
            "level_label": level_label,
            "findings": findings,
            "high_value_count": len(high_value),
        }
