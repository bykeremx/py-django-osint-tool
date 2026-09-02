# Playwright ile render edilmiş DOM + tarayıcının indirdiği asset'ler.
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import urlparse, unquote

MAX_FILES = 80
MAX_BYTES = 8 * 1024 * 1024
NAV_TIMEOUT_MS = 25_000
RESOURCE_TYPES = {"document", "stylesheet", "script", "image", "font"}
SOURCEMAP_RE = re.compile(rb"sourceMappingURL=([^\s*]+)")


class SiteSnapshot:
    @staticmethod
    def capture(domain: str) -> dict:
        url = f"https://{domain}" if not domain.startswith("http") else domain
        result = {
            "url": url,
            "save_dir": "",
            "files": [],
            "file_count": 0,
            "dom_preview": "",
            "error": None,
        }

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            result["error"] = "Playwright yok. Kurulum: pip install playwright && playwright install chromium"
            return result

        out_dir = SiteSnapshot._output_dir(domain)
        out_dir.mkdir(parents=True, exist_ok=True)
        result["save_dir"] = str(out_dir)

        saved: set[str] = set()
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                page = browser.new_page()

                def on_response(response):
                    if len(saved) >= MAX_FILES:
                        return
                    if response.request.resource_type not in RESOURCE_TYPES:
                        return
                    rel_path = SiteSnapshot._save_response(out_dir, response)
                    if rel_path:
                        saved.add(rel_path)

                page.on("response", on_response)
                page.goto(url, wait_until="networkidle", timeout=NAV_TIMEOUT_MS)
                rendered_html = page.content()
                (out_dir / "rendered-dom.html").write_text(rendered_html, encoding="utf-8")
                result["dom_preview"] = rendered_html[:4000]
                saved.add("rendered-dom.html")
                browser.close()
        except Exception as e:
            result["error"] = f"Playwright tarama hatası: {e}"
            return result

        SiteSnapshot._save_sourcemaps(out_dir, saved)
        result["files"] = sorted(saved)
        result["file_count"] = len(result["files"])
        return result

    @staticmethod
    def _output_dir(domain: str) -> Path:
        host = urlparse(f"https://{domain}").hostname or "snapshot"
        safe = "".join(ch if ch.isalnum() or ch in ".-" else "_" for ch in host)
        base = SiteSnapshot._media_root() / "site_snapshots" / safe
        return base

    @staticmethod
    def _media_root() -> Path:
        try:
            from django.conf import settings

            return Path(settings.MEDIA_ROOT)
        except Exception:
            return Path(__file__).resolve().parents[4] / "media"

    @staticmethod
    def _save_response(out_dir: Path, response) -> str | None:
        try:
            if not response.ok:
                return None
            body = response.body()
            if not body or len(body) > MAX_BYTES:
                return None
            rel = SiteSnapshot._relpath(response.url)
            target = (out_dir / rel).resolve()
            if not str(target).startswith(str(out_dir.resolve())):
                return None
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(body)
            return rel.replace("\\", "/")
        except Exception:
            return None

    @staticmethod
    def _relpath(url: str) -> str:
        parsed = urlparse(url)
        host = parsed.hostname or "asset"
        path = unquote(parsed.path or "")
        parts = [p for p in path.split("/") if p not in ("", ".", "..")]
        if not parts:
            parts = ["index.html"]
        elif "." not in parts[-1]:
            parts.append("index.html")
        return str(Path(host, *parts))

    @staticmethod
    def _save_sourcemaps(out_dir: Path, saved: set[str]) -> None:
        # Vue/React bundle içinde //# sourceMappingURL=... varsa .map dosyasını da çek
        import httpx

        extra = []
        for rel in list(saved):
            if not rel.endswith((".js", ".css")):
                continue
            data = (out_dir / rel).read_bytes()
            match = SOURCEMAP_RE.search(data)
            if not match:
                continue
            map_name = match.group(1).decode("utf-8", errors="ignore").strip()
            if map_name.startswith("data:"):
                continue
            map_url = SiteSnapshot._join_map_url(rel, map_name)
            extra.append(map_url)

        if not extra:
            return

        with httpx.Client(timeout=10.0, follow_redirects=True) as client:
            for map_url in extra:
                if len(saved) >= MAX_FILES:
                    break
                try:
                    response = client.get(map_url)
                    if response.status_code != 200 or len(response.content) > MAX_BYTES:
                        continue
                    rel = SiteSnapshot._relpath(str(response.url))
                    target = (out_dir / rel).resolve()
                    if not str(target).startswith(str(out_dir.resolve())):
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(response.content)
                    saved.add(rel.replace("\\", "/"))
                except Exception:
                    continue

    @staticmethod
    def _join_map_url(js_rel: str, map_name: str) -> str:
        if map_name.startswith("http"):
            return map_name
        # js_rel: cdn.example.com/assets/app.js -> https://cdn.example.com/assets/<map>
        host, *rest = js_rel.replace("\\", "/").split("/")
        folder = "/".join(rest[:-1])
        suffix = f"{folder}/{map_name}" if folder else map_name
        return f"https://{host}/{suffix}"
