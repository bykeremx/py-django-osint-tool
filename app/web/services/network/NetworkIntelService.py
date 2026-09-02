# Pasif ağ / tehdit istihbaratı: IP, ASN, TLS, DNS, InternetDB, risk özeti.
from __future__ import annotations

import ipaddress
import socket
import ssl
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import dns.resolver
import httpx
from ipwhois import IPWhois

# Bilinen yüksek riskli portlar (InternetDB kayıtları için)
HIGH_RISK_PORTS = {21, 22, 23, 445, 1433, 3306, 3389, 5432, 5900, 6379, 27017}
SECURITY_HEADERS = (
    "strict-transport-security",
    "content-security-policy",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
)


class NetworkIntelService:
    @classmethod
    def analyze(cls, domain: str) -> dict[str, Any]:
        raw = (domain or "").strip()
        is_ip = cls._is_ip(raw)

        if is_ip:
            addr = ipaddress.ip_address(raw)
            host = raw
            ipv4 = raw if addr.version == 4 else ""
            ipv6 = raw if addr.version == 6 else ""
            all_ipv4: list[str] = [ipv4] if ipv4 else []
        else:
            host = cls._normalize_host(raw)
            all_ipv4 = cls.resolve_all_ipv4(host)
            ipv4 = all_ipv4[0] if all_ipv4 else ""
            ipv6 = cls.resolve_ipv6(host)

        primary_ip = ipv4 or ipv6
        geo = cls.get_geoip_and_asn(primary_ip)
        rdap = cls.get_rdap(primary_ip)
        exposure = cls.get_shodan_host_info(primary_ip)

        result: dict[str, Any] = {
            "domain": host,
            "input_type": "ip" if is_ip else "domain",
            "ipv4": ipv4,
            "ipv6": ipv6,
            "all_ipv4": all_ipv4,
            "ptr": cls.reverse_ptr(primary_ip) if primary_ip else "",
            "geo": geo,
            "rdap": rdap,
            "exposure": exposure,
            "dns_intel": cls.get_dns_intel(host) if not is_ip else {},
            "tls": cls.get_tls_info(host if not is_ip else "", primary_ip),
            "security_headers": cls.get_security_headers(host if not is_ip else primary_ip),
            "infrastructure": cls.classify_infrastructure(geo, rdap, exposure),
            "reputation": cls.check_dnsbl(primary_ip),
            "threat": {},
            "error": None,
        }

        if not primary_ip and not is_ip:
            result["error"] = "Bu host için IP çözülemedi."

        result["threat"] = cls.build_threat_assessment(result)
        return result

    @staticmethod
    def _is_ip(value: str) -> bool:
        try:
            ipaddress.ip_address(value)
            return True
        except ValueError:
            return False

    @staticmethod
    def _normalize_host(domain: str) -> str:
        raw = (domain or "").strip().lower()
        if not raw:
            return ""
        if "://" not in raw:
            raw = f"http://{raw}"
        host = urlparse(raw).hostname or domain
        return host.strip(".").removeprefix("www.")

    @staticmethod
    def resolve_ip(domain: str) -> str:
        ips = NetworkIntelService.resolve_all_ipv4(domain)
        return ips[0] if ips else ""

    @staticmethod
    def resolve_all_ipv4(domain: str) -> list[str]:
        try:
            answers = dns.resolver.resolve(domain, "A")
            return sorted({str(rdata) for rdata in answers})
        except Exception:
            try:
                return [socket.gethostbyname(domain)]
            except Exception:
                return []

    @staticmethod
    def resolve_ipv6(domain: str) -> str:
        try:
            answers = dns.resolver.resolve(domain, "AAAA")
            return str(next(iter(answers))).rstrip(".")
        except Exception:
            return ""

    @staticmethod
    def reverse_ptr(ip: str) -> str:
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return ""

    @classmethod
    def get_dns_intel(cls, domain: str) -> dict[str, Any]:
        intel: dict[str, Any] = {
            "a": [],
            "aaaa": [],
            "mx": [],
            "ns": [],
            "txt": [],
            "spf": "",
            "dmarc": "",
            "caa": [],
        }
        if not domain:
            return intel

        resolver = dns.resolver.Resolver()
        resolver.lifetime = 4

        for rtype, key in (("A", "a"), ("AAAA", "aaaa"), ("NS", "ns")):
            try:
                answers = resolver.resolve(domain, rtype)
                intel[key] = [str(r).rstrip(".") for r in answers]
            except Exception:
                pass

        try:
            mx_answers = resolver.resolve(domain, "MX")
            intel["mx"] = sorted(
                f"{r.preference} {str(r.exchange).rstrip('.')}" for r in mx_answers
            )
        except Exception:
            pass

        try:
            txt_answers = resolver.resolve(domain, "TXT")
            for rdata in txt_answers:
                text = "".join(
                    p.decode("utf-8", errors="replace") if isinstance(p, bytes) else str(p)
                    for p in rdata.strings
                )
                intel["txt"].append(text)
                lower = text.lower()
                if lower.startswith("v=spf1"):
                    intel["spf"] = text
                if lower.startswith("v=dmarc1"):
                    intel["dmarc"] = text
        except Exception:
            pass

        try:
            caa_answers = resolver.resolve(domain, "CAA")
            intel["caa"] = [f"{r.tag} {r.value}" for r in caa_answers]
        except Exception:
            pass

        return intel

    @classmethod
    def get_tls_info(cls, domain: str, ip: str = "") -> dict[str, Any]:
        empty = {
            "host": domain or ip,
            "issuer": "",
            "subject": "",
            "not_before": "",
            "not_after": "",
            "days_left": None,
            "expired": False,
            "san": [],
            "protocol": "",
            "error": None,
        }
        target = domain or ip
        if not target:
            empty["error"] = "TLS hedefi yok"
            return empty

        try:
            context = ssl.create_default_context()
            with socket.create_connection((target, 443), timeout=8) as sock:
                with context.wrap_socket(sock, server_hostname=domain or target) as ssock:
                    cert = ssock.getpeercert()
                    empty["protocol"] = ssock.version() or ""
            if not cert:
                empty["error"] = "Sertifika alınamadı"
                return empty

            issuer = ", ".join(f"{k}={v}" for item in cert.get("issuer", ()) for k, v in item)
            subject = ", ".join(f"{k}={v}" for item in cert.get("subject", ()) for k, v in item)
            not_after = cert.get("notAfter", "")
            not_before = cert.get("notBefore", "")
            days_left = None
            expired = False
            if not_after:
                exp = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
                days_left = (exp - datetime.now(timezone.utc)).days
                expired = days_left < 0

            san = [entry[1] for entry in cert.get("subjectAltName", ()) if entry[0] == "DNS"]
            return {
                "host": target,
                "issuer": issuer,
                "subject": subject,
                "not_before": not_before,
                "not_after": not_after,
                "days_left": days_left,
                "expired": expired,
                "san": san[:20],
                "protocol": empty["protocol"],
                "error": None,
            }
        except Exception as e:
            empty["error"] = str(e)
            return empty

    @classmethod
    def get_security_headers(cls, host: str) -> dict[str, Any]:
        result: dict[str, Any] = {
            "url": "",
            "status_code": None,
            "present": [],
            "missing": [],
            "raw": {},
            "error": None,
        }
        if not host:
            return result

        url = f"https://{host}" if not host.startswith("http") else host
        if NetworkIntelService._is_ip(host):
            url = f"https://{host}"

        try:
            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                response = client.get(
                    url,
                    headers={"User-Agent": "CYBER-OPS-Intel/1.0"},
                )
            result["url"] = str(response.url)
            result["status_code"] = response.status_code
            headers = {k.lower(): v for k, v in response.headers.items()}
            result["raw"] = {h: headers[h] for h in SECURITY_HEADERS if h in headers}
            result["present"] = list(result["raw"].keys())
            result["missing"] = [h for h in SECURITY_HEADERS if h not in headers]
        except Exception as e:
            result["error"] = str(e)
        return result

    @classmethod
    def get_geoip_and_asn(cls, ip: str) -> dict[str, Any]:
        info = {
            "ip": ip,
            "country": "Bilinmiyor",
            "country_code": "",
            "region": "Bilinmiyor",
            "city": "Bilinmiyor",
            "lat": None,
            "lon": None,
            "isp": "Bilinmiyor",
            "org": "Bilinmiyor",
            "asn": "Bilinmiyor",
            "timezone": "Bilinmiyor",
            "hosting": False,
            "proxy": False,
        }
        if not ip:
            return info
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(
                    f"http://ip-api.com/json/{ip}",
                    params={
                        "fields": (
                            "status,country,countryCode,regionName,city,lat,lon,"
                            "isp,org,as,timezone,hosting,proxy,query"
                        )
                    },
                )
                data = response.json()
            if data.get("status") == "success":
                info.update(
                    {
                        "country": data.get("country") or "Bilinmiyor",
                        "country_code": data.get("countryCode") or "",
                        "region": data.get("regionName") or "Bilinmiyor",
                        "city": data.get("city") or "Bilinmiyor",
                        "lat": data.get("lat"),
                        "lon": data.get("lon"),
                        "isp": data.get("isp") or "Bilinmiyor",
                        "org": data.get("org") or "Bilinmiyor",
                        "asn": data.get("as") or "Bilinmiyor",
                        "timezone": data.get("timezone") or "Bilinmiyor",
                        "hosting": bool(data.get("hosting")),
                        "proxy": bool(data.get("proxy")),
                    }
                )
        except Exception:
            pass
        return info

    @staticmethod
    def get_rdap(ip: str) -> dict[str, Any]:
        empty = {
            "asn": "Bilinmiyor",
            "asn_cidr": "Bilinmiyor",
            "asn_country": "Bilinmiyor",
            "asn_description": "Bilinmiyor",
            "network_name": "Bilinmiyor",
            "network_cidr": "Bilinmiyor",
        }
        if not ip:
            return empty
        try:
            lookup = IPWhois(ip).lookup_rdap(depth=1)
            network = lookup.get("network") or {}
            return {
                "asn": lookup.get("asn") or "Bilinmiyor",
                "asn_cidr": lookup.get("asn_cidr") or "Bilinmiyor",
                "asn_country": lookup.get("asn_country_code") or "Bilinmiyor",
                "asn_description": lookup.get("asn_description") or "Bilinmiyor",
                "network_name": network.get("name") or "Bilinmiyor",
                "network_cidr": network.get("cidr") or "Bilinmiyor",
            }
        except Exception:
            return empty

    @staticmethod
    def get_shodan_host_info(ip: str, api_key: str = "") -> dict[str, Any]:
        empty: dict[str, Any] = {
            "ports": [],
            "hostnames": [],
            "tags": [],
            "cves": [],
            "cpes": [],
            "high_risk_ports": [],
            "error": None,
        }
        if not ip:
            return empty
        try:
            with httpx.Client(timeout=8.0) as client:
                response = client.get(f"https://internetdb.shodan.io/{ip}")
            if response.status_code == 404:
                return empty
            if response.status_code != 200:
                empty["error"] = f"InternetDB HTTP {response.status_code}"
                return empty
            data = response.json()
            ports = sorted(data.get("ports") or [])
            cves = data.get("vulns") or []
            if isinstance(cves, dict):
                cves = list(cves.keys())
            empty.update(
                {
                    "ports": ports,
                    "hostnames": data.get("hostnames") or [],
                    "tags": data.get("tags") or [],
                    "cves": sorted(str(c) for c in cves)[:50],
                    "cpes": (data.get("cpes") or [])[:15],
                    "high_risk_ports": [p for p in ports if p in HIGH_RISK_PORTS],
                }
            )
        except Exception as e:
            empty["error"] = str(e)
        return empty

    @staticmethod
    def check_dnsbl(ip: str) -> dict[str, Any]:
        """Pasif DNSBL (Spamhaus zen) — listed / temiz."""
        result: dict[str, Any] = {"listed": [], "clean": True, "error": None}
        if not ip or not NetworkIntelService._is_ip(ip):
            return result
        try:
            addr = ipaddress.ip_address(ip)
            if addr.version != 4:
                result["error"] = "DNSBL yalnızca IPv4"
                return result
            reversed_ip = ".".join(reversed(ip.split(".")))
            query = f"{reversed_ip}.zen.spamhaus.org"
            answers = dns.resolver.resolve(query, "A")
            codes = {str(r) for r in answers}
            if "127.0.0.2" in codes:
                result["listed"].append("Spamhaus SBL")
            if "127.0.0.3" in codes:
                result["listed"].append("Spamhaus CSS")
            if "127.0.0.4" in codes:
                result["listed"].append("Spamhaus XBL")
            result["clean"] = not result["listed"]
        except dns.resolver.NXDOMAIN:
            result["clean"] = True
        except Exception as e:
            result["error"] = str(e)
        return result

    @staticmethod
    def classify_infrastructure(
        geo: dict[str, Any], rdap: dict[str, Any], exposure: dict[str, Any]
    ) -> dict[str, Any]:
        blob = " ".join(
            [
                str(geo.get("org", "")),
                str(geo.get("isp", "")),
                str(geo.get("asn", "")),
                str(rdap.get("asn_description", "")),
                " ".join(exposure.get("tags") or []),
            ]
        ).lower()

        providers = [
            ("Cloudflare", ("cloudflare",)),
            ("Amazon AWS", ("amazon", "aws", "ec2")),
            ("Google Cloud", ("google", "gcp")),
            ("Microsoft Azure", ("microsoft", "azure")),
            ("DigitalOcean", ("digitalocean",)),
            ("Hetzner", ("hetzner",)),
            ("OVH", ("ovh",)),
            ("Akamai", ("akamai",)),
        ]
        provider = "Bilinmiyor / On-prem"
        for name, needles in providers:
            if any(n in blob for n in needles):
                provider = name
                break

        return {
            "provider": provider,
            "hosting": geo.get("hosting", False),
            "proxy_or_cdn": geo.get("proxy", False),
            "tags": exposure.get("tags") or [],
        }

    @staticmethod
    def build_threat_assessment(intel: dict[str, Any]) -> dict[str, Any]:
        findings: list[dict[str, str]] = []
        score = 0

        exposure = intel.get("exposure") or {}
        tls = intel.get("tls") or {}
        headers = intel.get("security_headers") or {}
        reputation = intel.get("reputation") or {}

        for port in exposure.get("high_risk_ports") or []:
            findings.append({"level": "high", "text": f"InternetDB: yüksek riskli port {port} kayıtlı"})
            score += 25

        cve_count = len(exposure.get("cves") or [])
        if cve_count:
            findings.append({"level": "high", "text": f"InternetDB: {cve_count} CVE kimliği (doğrulanmamış)"})
            score += min(40, cve_count * 8)

        if tls.get("expired"):
            findings.append({"level": "high", "text": "TLS sertifikası süresi dolmuş"})
            score += 30
        elif tls.get("days_left") is not None and tls["days_left"] < 30:
            findings.append({"level": "medium", "text": f"TLS sertifikası {tls['days_left']} gün içinde bitiyor"})
            score += 15

        missing = headers.get("missing") or []
        if "strict-transport-security" in missing:
            findings.append({"level": "medium", "text": "HSTS (Strict-Transport-Security) yok"})
            score += 10
        if len(missing) >= 4:
            findings.append({"level": "low", "text": f"{len(missing)} güvenlik başlığı eksik"})
            score += 5

        if not reputation.get("clean") and reputation.get("listed"):
            findings.append({"level": "high", "text": f"DNSBL listesi: {', '.join(reputation['listed'])}"})
            score += 35

        honeypot_tags = {"honeypot", "malware", "botnet", "tor"}
        for tag in exposure.get("tags") or []:
            if tag.lower() in honeypot_tags:
                findings.append({"level": "high", "text": f"InternetDB etiketi: {tag}"})
                score += 20

        if not findings:
            findings.append({"level": "info", "text": "Belirgin tehdit göstergesi yok (pasif kaynaklara göre)"})

        score = min(100, score)
        if score >= 60:
            level = "yüksek"
        elif score >= 30:
            level = "orta"
        elif score >= 10:
            level = "düşük"
        else:
            level = "minimal"

        return {"score": score, "level": level, "findings": findings}
