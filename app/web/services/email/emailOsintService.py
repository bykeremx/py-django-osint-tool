# Email OSINT orchestrator: doğrulama + footprint + hesap varlığı.
from __future__ import annotations

import time
from typing import Any

from app.web.services.email.emailFootprintService import EmailFootprintService
from app.web.services.email.emailValidationService import EmailValidationService
from app.web.services.email.holeheAccountService import HoleheAccountService


class EmailOsintService:
    @classmethod
    def analyze(cls, email: str, *, include_accounts: bool = True) -> dict[str, Any]:
        started = time.time()
        validation = EmailValidationService.analyze(email)

        if not validation.get("valid"):
            return {
                "error": validation.get("error", "Geçersiz e-posta."),
                "email": email,
                "validation": validation,
                "footprint": None,
                "accounts": None,
                "elapsed_seconds": round(time.time() - started, 2),
            }

        normalized = validation["normalized"]
        domain = validation["domain"]

        footprint = EmailFootprintService.analyze(normalized, domain)
        accounts = HoleheAccountService.scan(normalized) if include_accounts else None

        return {
            "error": None,
            "email": normalized,
            "validation": validation,
            "footprint": footprint,
            "accounts": accounts,
            "elapsed_seconds": round(time.time() - started, 2),
        }
