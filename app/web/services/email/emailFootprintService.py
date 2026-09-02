# E-posta domain footprint: MX, SPF, DMARC, Gravatar, WHOIS.
from __future__ import annotations

import hashlib
from typing import Any

import dns.resolver
import httpx
import whois

DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "10minutemail.com", "tempmail.com",
    "throwaway.email", "yopmail.com", "sharklasers.com", "trashmail.com",
    "getnada.com", "maildrop.cc", "dispostable.com",
}


class EmailFootprintService:
    @classmethod
    def analyze(cls, email: str, domain: str) -> dict[str, Any]:
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 8.0

        mx = cls._mx_records(resolver, domain)
        txt = cls._txt_records(resolver, domain)
        spf = cls._extract_spf(txt)
        dmarc = cls._dmarc_record(resolver, domain)
        ns = cls._ns_records(resolver, domain)
        gravatar = cls._gravatar_check(email)
        whois_data = cls._whois_summary(domain)

        return {
            "domain": domain,
            "mx": mx,
            "spf": spf,
            "dmarc": dmarc,
            "ns": ns,
            "gravatar": gravatar,
            "whois": whois_data,
            "disposable_domain": domain in DISPOSABLE_DOMAINS,
            "mail_infrastructure": cls._infer_mail_stack(mx, spf),
        }

    @staticmethod
    def _mx_records(resolver: dns.resolver.Resolver, domain: str) -> dict[str, Any]:
        try:
            answers = resolver.resolve(domain, "MX")
            records = sorted(
                {"priority": r.preference, "host": str(r.exchange).rstrip(".")}
                for r in answers
            )
            return {"available": True, "records": records, "error": None}
        except Exception as e:
            return {"available": False, "records": [], "error": str(e)}

    @staticmethod
    def _txt_records(resolver: dns.resolver.Resolver, domain: str) -> list[str]:
        try:
            answers = resolver.resolve(domain, "TXT")
            return ["".join(part.decode() if isinstance(part, bytes) else str(part) for part in r.strings) for r in answers]
        except Exception:
            return []

    @staticmethod
    def _extract_spf(txt_records: list[str]) -> dict[str, Any]:
        for record in txt_records:
            if record.lower().startswith("v=spf1"):
                includes = [part[8:] for part in record.split() if part.lower().startswith("include:")]
                return {"available": True, "record": record, "includes": includes}
        return {"available": False, "record": None, "includes": []}

    @staticmethod
    def _dmarc_record(resolver: dns.resolver.Resolver, domain: str) -> dict[str, Any]:
        try:
            answers = resolver.resolve(f"_dmarc.{domain}", "TXT")
            for r in answers:
                text = "".join(
                    part.decode() if isinstance(part, bytes) else str(part) for part in r.strings
                )
                if text.lower().startswith("v=dmarc1"):
                    policy = "none"
                    for part in text.split(";"):
                        part = part.strip()
                        if part.lower().startswith("p="):
                            policy = part.split("=", 1)[1].strip()
                    return {"available": True, "record": text, "policy": policy, "error": None}
            return {"available": False, "record": None, "policy": None, "error": "DMARC TXT bulunamadı."}
        except Exception as e:
            return {"available": False, "record": None, "policy": None, "error": str(e)}

    @staticmethod
    def _ns_records(resolver: dns.resolver.Resolver, domain: str) -> dict[str, Any]:
        try:
            answers = resolver.resolve(domain, "NS")
            hosts = sorted(str(r).rstrip(".") for r in answers)
            return {"available": True, "hosts": hosts, "error": None}
        except Exception as e:
            return {"available": False, "hosts": [], "error": str(e)}

    @staticmethod
    def _gravatar_check(email: str) -> dict[str, Any]:
        normalized = email.strip().lower().encode()
        digest = hashlib.md5(normalized).hexdigest()
        url = f"https://www.gravatar.com/avatar/{digest}?d=404"
        try:
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                response = client.get(url)
                exists = response.status_code == 200
                profile_url = f"https://gravatar.com/{digest}" if exists else None
                return {
                    "hash": digest,
                    "exists": exists,
                    "profile_url": profile_url,
                    "avatar_url": url if exists else None,
                    "error": None,
                }
        except Exception as e:
            return {"hash": digest, "exists": False, "profile_url": None, "avatar_url": None, "error": str(e)}

    @staticmethod
    def _whois_summary(domain: str) -> dict[str, Any]:
        try:
            data = whois.whois(domain)
            registrar = data.registrar or "—"
            if isinstance(registrar, list):
                registrar = registrar[0] if registrar else "—"
            created = data.creation_date
            if isinstance(created, list):
                created = created[0]
            expires = data.expiration_date
            if isinstance(expires, list):
                expires = expires[0]
            return {
                "available": True,
                "registrar": str(registrar),
                "created": str(created) if created else None,
                "expires": str(expires) if expires else None,
                "name_servers": data.name_servers[:5] if data.name_servers else [],
                "error": None,
            }
        except Exception as e:
            return {"available": False, "registrar": None, "created": None, "expires": None, "name_servers": [], "error": str(e)}

    @staticmethod
    def _infer_mail_stack(mx: dict, spf: dict) -> list[str]:
        hints: list[str] = []
        hosts = " ".join(r["host"].lower() for r in mx.get("records", []))
        spf_text = (spf.get("record") or "").lower()

        providers = (
            ("google", ("google.com", "googlemail.com", "aspmx")),
            ("microsoft", ("outlook.com", "protection.outlook.com", "microsoft")),
            ("cloudflare", ("cloudflare.net",)),
            ("zoho", ("zoho.com", "zoho.eu")),
            ("proton", ("protonmail.ch", "proton.me")),
            ("yandex", ("yandex.net",)),
            ("mailgun", ("mailgun.org",)),
            ("sendgrid", ("sendgrid.net",)),
        )
        for name, needles in providers:
            if any(n in hosts or n in spf_text for n in needles):
                hints.append(name)
        return hints or (["unknown"] if mx.get("available") else [])
