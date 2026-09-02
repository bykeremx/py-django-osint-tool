# DNS recon servisi: kayıt toplama, PTR ve WHOIS.
from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

import dns.resolver
import whois

import httpx

from wappalyzer.Wappalyzer import Wappalyzer, WebPage

class DnsServices:
    # Sorgulanacak DNS kayıt türleri (A=IPv4, AAAA=IPv6, MX=posta, SOA=zone yetkisi vb.)
    RECORD_TYPES = ("A", "AAAA", "CNAME", "MX", "NS", "TXT", "SOA", "CAA", "SRV")

    @staticmethod
    def web_analisis(domain: str) -> dict:
        """HTTPS GET: başlıklar, çerez, HTML imzası, Wappalyzer ve backend dili tahmini."""
        url = f"https://{domain}" if not domain.startswith("http") else domain
        http_results = {
            "url": url,
            "status_code": None,
            "headers": {},
            "cookies": {},
            "technologies": [],
            "backend": [],
            "error": None,
        }

        headers_in = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        try:
            with httpx.Client(timeout=15.0, follow_redirects=True, headers=headers_in) as client:
                response = client.get(url)
                html = response.text[:250_000]
                header_map = {k.lower(): v for k, v in response.headers.items()}
                cookies = {k: v for k, v in response.cookies.items()}
                http_results["status_code"] = response.status_code
                http_results["url"] = str(response.url)
                http_results["headers"] = dict(response.headers)
                http_results["cookies"] = cookies
        except Exception as e:
            http_results["error"] = f"HTTP tarama hatası: {e}"
            return http_results

        try:
            wappalyzer = Wappalyzer.latest()
            webpage = WebPage(str(response.url), html, dict(response.headers))
            if hasattr(wappalyzer, "analyze_with_categories"):
                categorized = wappalyzer.analyze_with_categories(webpage)
                http_results["technologies"] = sorted(
                    f"{name} ({', '.join(cats)})" if cats else name
                    for name, cats in categorized.items()
                )
            else:
                http_results["technologies"] = sorted(str(item) for item in wappalyzer.analyze(webpage))
        except Exception as e:
            http_results["error"] = f"Teknoloji tespiti hatası: {e}"

        http_results["backend"] = DnsServices._infer_backend(
            header_map, cookies, html, http_results["technologies"]
        )
        return http_results

    @staticmethod
    def _infer_backend(headers: dict, cookies: dict, html: str, technologies: list[str]) -> list[dict]:
        """Başlık / çerez / HTML / Wappalyzer ipuçlarından backend dili ve çerçeve tahmini."""
        blob = " ".join(
            [
                " ".join(f"{k}:{v}" for k, v in headers.items()),
                " ".join(cookies.keys()),
                html[:80_000],
                " ".join(technologies),
            ]
        ).lower()
        cookie_names = {name.lower() for name in cookies}

        rules = [
            ("PHP", "PHP", ("x-powered-by: php", "phpsessid", "wp-content", "wp-includes", "laravel_session", ".php")),
            ("Laravel", "PHP", ("laravel_session", "x-powered-by: laravel")),
            ("WordPress", "PHP", ("wp-content", "wp-includes", "wordpress")),
            ("Python / Django", "Python", ("csrfmiddlewaretoken", "djdt", "wsgiserver", "gunicorn", "djangoproject")),
            ("Python / Flask", "Python", ("werkzeug", "flask", "session=")),
            ("Python / FastAPI", "Python", ("fastapi", "uvicorn")),
            ("Ruby / Rails", "Ruby", ("x-runtime", "phusion", "_session_id", "authenticity_token", "ruby")),
            ("Java", "Java", ("jsessionid", "servlet", "tomcat", "jetty", "weblogic", "jboss", "spring")),
            ("ASP.NET", "C# / .NET", ("x-aspnet", "asp.net", "x-powered-by: asp.net", "__viewstate", ".aspx")),
            ("ASP.NET Core", "C# / .NET", (".aspnetcore", "x-powered-by: asp.net core")),
            ("Node.js", "JavaScript", ("x-powered-by: express", "express", "connect.sid", "next.js", "nuxt", "node.js")),
            ("Go", "Go", ("golang", "gin-gonic", "x-powered-by: go")),
            ("Elixir / Phoenix", "Elixir", ("phoenix", "_phoenix_key", "elixir")),
            ("Perl", "Perl", ("plack", "catalyst", "x-powered-by: perl")),
        ]

        found: dict[str, dict] = {}
        for label, language, needles in rules:
            hits = [n for n in needles if n in blob or n in cookie_names]
            if not hits:
                continue
            entry = found.setdefault(label, {"name": label, "language": language, "evidence": []})
            for hit in hits:
                if hit not in entry["evidence"]:
                    entry["evidence"].append(hit)

        server = headers.get("server") or headers.get("x-powered-by")
        if server and not found:
            found["Sunucu imzası"] = {
                "name": "Sunucu imzası",
                "language": server,
                "evidence": [server],
            }

        return sorted(found.values(), key=lambda item: item["name"])

    @staticmethod
    def dns_scan_service(domain: str) -> dict:
        """View katmanının çağırdığı ana giriş noktası. Şablona gidecek dict üretir."""
        # URL / www / path temizlenmiş FQDN
        domain = DnsServices._normalize_domain(domain)
        results = {
            "domain": domain,
            "dns": {},
            "reverse_dns": [],
            "whois": {},
        }

        # Tek resolver; timeout 5 sn (yavaş NS'te sayfanın kilitlenmesini sınırlar)
        resolver = dns.resolver.Resolver()
        resolver.lifetime = 5

        # Tür yoksa boş liste; tarama kırılmasın diye exception yutulur
        for record_type in DnsServices.RECORD_TYPES:
            results["dns"][record_type] = DnsServices._resolve_records(
                resolver, domain, record_type
            )

        # PTR yalnızca A kayıtlarındaki IPv4'ler için
        ipv4_addresses = [
            value for value in results["dns"].get("A", []) if DnsServices._is_ipv4(value)
        ]
        results["reverse_dns"] = DnsServices._reverse_lookup(ipv4_addresses)
        results["subdomains"] = DnsServices._discover_subdomains(resolver, domain)
        results["whois"] = DnsServices._whois_lookup(domain)
        results["web_analisis"] = DnsServices.web_analisis(domain)
        from app.web.services.dns.siteSnapshot import SiteSnapshot

        results["site_snapshot"] = SiteSnapshot.capture(domain)
        return results

    SUBDOMAIN_PREFIXES = (
        "www", "mail", "ftp", "api", "admin", "dev", "staging", "test",
        "vpn", "ns1", "ns2", "blog", "shop", "cdn", "app", "portal",
        "remote", "git", "status", "docs", "m", "webmail", "smtp",
        "imap", "mx", "cloud", "beta", "demo", "sso", "auth", "login",
    )

    @staticmethod
    def _discover_subdomains(resolver: dns.resolver.Resolver, domain: str) -> dict:
        """CT (crt.sh) + kısa wordlist; yalnızca DNS'te çözülenler döner."""
        result = {"items": [], "error": None, "sources": {"ct": 0, "wordlist": 0}}
        candidates: dict[str, set[str]] = {}

        for name in DnsServices._crtsh_names(domain):
            candidates.setdefault(name, set()).add("ct")
        result["sources"]["ct"] = sum(1 for tags in candidates.values() if "ct" in tags)

        for prefix in DnsServices.SUBDOMAIN_PREFIXES:
            name = f"{prefix}.{domain}".lower()
            candidates.setdefault(name, set()).add("wordlist")
        result["sources"]["wordlist"] = len(DnsServices.SUBDOMAIN_PREFIXES)

        previous_lifetime = resolver.lifetime
        resolver.lifetime = 2
        items = []
        for name in sorted(candidates):
            if len(items) >= 80:
                break
            resolved = DnsServices._resolve_subdomain(resolver, name)
            if not resolved:
                continue
            items.append({
                "host": name,
                "records": resolved,
                "sources": sorted(candidates[name]),
            })
        resolver.lifetime = previous_lifetime

        result["items"] = items
        return result

    @staticmethod
    def _crtsh_names(domain: str) -> list[str]:
        url = f"https://crt.sh/?q=%25.{domain}&output=json"
        names: set[str] = set()
        try:
            with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                response = client.get(url, headers={"User-Agent": "CYBER-OPS-recon/1.0"})
                if response.status_code != 200:
                    return []
                rows = response.json()
        except Exception:
            return []

        suffix = f".{domain}"
        if not isinstance(rows, list):
            return []
        for row in rows:
            value = (row.get("name_value") or "") if isinstance(row, dict) else ""
            for raw in value.split("\n"):
                host = raw.strip().lower().rstrip(".")
                if host.startswith("*."):
                    host = host[2:]
                if host == domain or host.endswith(suffix):
                    if " " not in host and host.count(".") >= domain.count("."):
                        names.add(host)
                if len(names) >= 200:
                    return sorted(names)
        return sorted(names)

    @staticmethod
    def _resolve_subdomain(resolver: dns.resolver.Resolver, name: str) -> list[str]:
        records = []
        for rtype in ("A", "AAAA", "CNAME"):
            try:
                answers = resolver.resolve(name, rtype)
                records.extend(f"{rtype} {str(rdata).rstrip('.')}" for rdata in answers)
            except Exception:
                continue
        return records

    @staticmethod
    def _normalize_domain(domain: str) -> str:
        """https://www.ornek.com/path -> ornek.com"""
        raw = (domain or "").strip().lower()
        if not raw:
            return ""

        # urlparse host'u ayırsın diye şema yoksa eklenir (istek atılmaz)
        if "://" not in raw:
            raw = f"http://{raw}"

        parsed = urlparse(raw)
        host = parsed.hostname or domain
        host = host.strip(".").strip("/")
        if host.startswith("www."):
            host = host[4:]
        return host

    @staticmethod
    def _resolve_records(resolver: dns.resolver.Resolver, domain: str, record_type: str) -> list[str]:
        # NXDOMAIN / NoAnswer / timeout -> []
        try:
            answers = resolver.resolve(domain, record_type)
            return [DnsServices._format_rdata(record_type, rdata) for rdata in answers]
        except Exception:
            return []

    @staticmethod
    def _format_rdata(record_type: str, rdata) -> str:
        """Ham rdata'yı şablonda okunabilir string yapar."""
        # MX: öncelik + mail sunucusu
        if record_type == "MX":
            return f"{rdata.preference} {str(rdata.exchange).rstrip('.')}"
        # SOA: primary NS, responsible mail, zone timer'ları
        if record_type == "SOA":
            return (
                f"mname={str(rdata.mname).rstrip('.')} "
                f"rname={str(rdata.rname).rstrip('.')} "
                f"serial={rdata.serial} refresh={rdata.refresh} "
                f"retry={rdata.retry} expire={rdata.expire} minimum={rdata.minimum}"
            )
        # CAA: hangi CA sertifika basabilir
        if record_type == "CAA":
            return f"{rdata.flags} {rdata.tag} {rdata.value}"
        # SRV: servis keşfi (öncelik, ağırlık, port, hedef)
        if record_type == "SRV":
            return (
                f"{rdata.priority} {rdata.weight} {rdata.port} "
                f"{str(rdata.target).rstrip('.')}"
            )
        # TXT parçaları bazen bytes gelir (SPF, DMARC, DKIM)
        if record_type == "TXT":
            return "".join(
                part.decode("utf-8", errors="replace") if isinstance(part, bytes) else str(part)
                for part in rdata.strings
            )
        # Trailing dot FQDN gösterimini sadeleştirir
        return str(rdata).rstrip(".")

    @staticmethod
    def _is_ipv4(value: str) -> bool:
        # A listesine yanlışlıkla hostname karışırsa PTR sorgusu yapılmasın
        parts = value.split(".")
        if len(parts) != 4:
            return False
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)

    @staticmethod
    def _reverse_lookup(addresses: list[str]) -> list[dict]:
        """IP -> PTR hostname. Kayıt yoksa hostnames boş kalır."""
        entries = []
        for ip in addresses:
            try:
                answers = dns.resolver.resolve_address(ip)
                hostnames = [str(rdata).rstrip(".") for rdata in answers]
            except Exception:
                hostnames = []
            entries.append({"ip": ip, "hostnames": hostnames})
        return entries

    @staticmethod
    def _whois_lookup(domain: str) -> dict:
        """python-whois. Alanlar registrar'a göre list veya tek değer olabilir."""
        try:
            w = whois.whois(domain)
        except Exception as e:
            return {"error": f"WHOIS bilgisi çekilemedi: {e}"}

        emails = DnsServices._as_list(getattr(w, "emails", None))
        nameservers = [
            str(ns).rstrip(".").lower()
            for ns in DnsServices._as_list(getattr(w, "name_servers", None))
        ]
        statuses = DnsServices._as_list(getattr(w, "status", None))

        # getattr: bazı TLD'lerde alan hiç yok
        return {
            "registrar": DnsServices._first(getattr(w, "registrar", None)) or "Bilinmiyor",
            "whois_server": DnsServices._first(getattr(w, "whois_server", None)) or "Bilinmiyor",
            "org": DnsServices._first(getattr(w, "org", None)) or "Bilinmiyor",
            "registrant": DnsServices._first(getattr(w, "name", None)) or "Bilinmiyor",
            "country": DnsServices._first(getattr(w, "country", None)) or "Bilinmiyor",
            "creation_date": DnsServices._format_date(getattr(w, "creation_date", None)),
            "updated_date": DnsServices._format_date(getattr(w, "updated_date", None)),
            "expiration_date": DnsServices._format_date(getattr(w, "expiration_date", None)),
            "emails": emails,
            "name_servers": sorted(set(nameservers)),  # tekrarlı NS birleştirilir
            "status": statuses,
            "dnssec": DnsServices._first(getattr(w, "dnssec", None)) or "Bilinmiyor",
        }

    @staticmethod
    def _as_list(value) -> list[str]:
        # WHOIS bazen str, bazen list döner — şablon hep liste bekler
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return [str(item) for item in value if item]
        return [str(value)]

    @staticmethod
    def _first(value):
        # Tarih/registrar list geldiyse ilk eleman kullanılır
        if isinstance(value, (list, tuple)) and value:
            return value[0]
        return value

    @staticmethod
    def _format_date(value) -> str:
        value = DnsServices._first(value)
        if not value:
            return "Bilinmiyor"
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)
