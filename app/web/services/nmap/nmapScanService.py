# Nmap port / servis taraması (python-nmap).
from __future__ import annotations

import time
from typing import Any

SCAN_PROFILES = {
    "quick": {
        "label": "Hızlı (top 100 port)",
        "arguments": "-sT -F -T4",
    },
    "standard": {
        "label": "Standart (top 1000 + servis)",
        "arguments": "-sT -sV -T4 --top-ports 1000",
    },
    "deep": {
        "label": "Derin (tüm portlar + servis)",
        "arguments": "-sT -sV -p- -T4",
    },
}


class NmapScanService:
    @classmethod
    def scan(cls, target: str, *, mode: str = "standard") -> dict[str, Any]:
        target = (target or "").strip()
        if not target:
            return {"error": "Hedef boş.", "target": target}

        profile = SCAN_PROFILES.get(mode, SCAN_PROFILES["standard"])
        started = time.time()

        try:
            import nmap
        except ImportError:
            return cls._error(
                target,
                mode,
                "python-nmap kurulu değil. pip install python-nmap",
                elapsed=0,
            )

        try:
            scanner = nmap.PortScanner()
        except nmap.PortScannerError as e:
            return cls._error(
                target,
                mode,
                f"Nmap binary bulunamadı. Nmap'i kurun ve PATH'e ekleyin. ({e})",
                elapsed=0,
            )

        try:
            scanner.scan(hosts=target, arguments=profile["arguments"])
        except nmap.PortScannerError as e:
            return cls._error(target, mode, str(e), time.time() - started)
        except Exception as e:
            return cls._error(target, mode, f"Tarama hatası: {e}", time.time() - started)

        hosts = cls._parse_hosts(scanner)
        open_ports = sum(len(h["ports"]) for h in hosts)
        hosts_up = sum(1 for h in hosts if h["state"] == "up")

        return {
            "error": None,
            "target": target,
            "scan_mode": mode,
            "scan_mode_label": profile["label"],
            "nmap_command": scanner.command_line(),
            "scan_stats": dict(scanner.scanstats()) if scanner.scanstats() else {},
            "hosts": hosts,
            "summary": {
                "hosts_total": len(hosts),
                "hosts_up": hosts_up,
                "open_ports": open_ports,
                "elapsed_seconds": round(time.time() - started, 2),
            },
        }

    @staticmethod
    def _parse_hosts(scanner) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for host in scanner.all_hosts():
            host_data = scanner[host]
            hostname = (host_data.hostname() or "").strip()
            state = host_data.state()

            ports: list[dict[str, Any]] = []
            for proto in host_data.all_protocols():
                for port in sorted(host_data[proto].keys()):
                    info = host_data[proto][port]
                    if info.get("state") != "open":
                        continue
                    ports.append({
                        "port": port,
                        "protocol": proto,
                        "state": info.get("state", ""),
                        "service": info.get("name", ""),
                        "product": info.get("product", ""),
                        "version": info.get("version", ""),
                        "extrainfo": info.get("extrainfo", ""),
                        "cpe": info.get("cpe", ""),
                    })

            results.append({
                "host": host,
                "hostname": hostname,
                "state": state,
                "ports": ports,
            })

        results.sort(key=lambda h: (-len(h["ports"]), h["host"]))
        return results

    @staticmethod
    def _error(target: str, mode: str, message: str, elapsed: float) -> dict[str, Any]:
        return {
            "error": message,
            "target": target,
            "scan_mode": mode,
            "scan_mode_label": SCAN_PROFILES.get(mode, {}).get("label", mode),
            "nmap_command": None,
            "scan_stats": {},
            "hosts": [],
            "summary": {
                "hosts_total": 0,
                "hosts_up": 0,
                "open_ports": 0,
                "elapsed_seconds": round(elapsed, 2),
            },
        }
