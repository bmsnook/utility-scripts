#!/usr/bin/env python3
"""
Download a URL using a headless browser so that JavaScript runs and the server
can return the real file (or trigger a download) instead of an HTML "enable JS" page.

Uses Playwright (Chromium). Auth is read from ~/.auth/site_auth/<domain> (same as
download_with_bearer.py). Install: pip install playwright && playwright install chromium.

Usage:
  download_with_js.py <url> [<url> ...] [-o DIR] [-d]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

# Same paths as download_with_bearer.py
SITE_AUTH_DIR = os.path.expanduser("~/.auth/site_auth")
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
CHROME_AGENT_FILE = os.path.expanduser("~/.chrome_agent")

# Content types we treat as the "real" file (not the HTML shell)
FILE_LIKE_CONTENT_TYPES = (
    "application/octet-stream",
    "application/pdf",
    "application/zip",
    "application/gzip",
    "application/x-tar",
    "application/x-gzip",
)


def get_user_agent() -> str:
    path = Path(CHROME_AGENT_FILE)
    if path.is_file():
        return path.read_text().strip() or DEFAULT_USER_AGENT
    return DEFAULT_USER_AGENT


def domain_from_url(url: str) -> str:
    netloc = urlparse(url).netloc or ""
    return netloc.replace(":", "_") if netloc else ""


def get_domain_headers(domain: str, cache: dict[str, dict[str, str]]) -> dict[str, str] | None:
    """Load auth headers from ~/.auth/site_auth/<domain>. Same logic as download_with_bearer."""
    if domain in cache:
        return cache[domain]
    auth_dir = Path(SITE_AUTH_DIR)
    auth_file = auth_dir / domain
    if not auth_file.is_file():
        return None
    lines = [
        line.strip()
        for line in auth_file.read_text().splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not lines:
        return None
    headers = {}
    for line in lines:
        if line.startswith("bearer_token="):
            value = line[len("bearer_token=") :].strip()
            if value:
                headers["Authorization"] = f"Bearer {value}"
        elif ": " in line:
            key, _, value = line.partition(": ")
            key = key.strip()
            if key:
                headers[key] = value.strip()
        else:
            if len(lines) == 1:
                headers["Authorization"] = f"Bearer {line}"
            break
    cache[domain] = headers
    return headers


def _cookie_header_to_playwright_cookies(cookie_header: str, domain: str) -> list[dict]:
    """Turn a 'Cookie: name1=val1; name2=val2' header into Playwright cookie list."""
    if not cookie_header or not domain:
        return []
    cookies = []
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" in part:
            name, _, value = part.partition("=")
            name, value = name.strip(), value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": "/",
                })
    return cookies


def _looks_like_file_response(content_type: str | None, content_disp: str | None) -> bool:
    if content_disp and "attachment" in content_disp.lower():
        return True
    if not content_type:
        return False
    ct = content_type.lower().split(";")[0].strip()
    if "text/html" in ct or ct == "text/plain":
        return False
    if any(ct.startswith(t) for t in FILE_LIKE_CONTENT_TYPES):
        return True
    if ct.startswith("application/") or ct.startswith("image/") or ct.startswith("video/"):
        return True
    return False


def deduce_filename(url: str) -> str:
    """Derive a safe local filename from the URL. Mirrors download_with_bearer logic."""
    p = urlparse(url)
    path = unquote(p.path or "").strip("/")
    netloc = p.netloc.replace(":", "_")
    segments = [s for s in path.split("/") if s]
    last = segments[-1] if segments else ""

    def sanitize(name: str) -> str:
        name = re.sub(r'[<>:"/\\|?*]', "_", name)
        return name.strip(". ") or "download"

    if last:
        if "." in last and not last.startswith("."):
            base, ext = last.rsplit(".", 1)
            if len(ext) <= 5 and base:
                return sanitize(last)
        if segments and last not in ("api", "v1", "v2", "v3", ""):
            return sanitize(last)
    if path:
        path_slug = sanitize(path.replace("/", "_"))
        name = f"{netloc}_{path_slug}" if netloc else path_slug
    else:
        name = netloc or "download"
    if p.query:
        name += "_" + hashlib.md5(p.query.encode(), usedforsecurity=False).hexdigest()[:8]
    if not re.search(r"\.\w+$", name):
        name += ".bin"
    return name


def add_date_suffix(filename: str, date_str: str) -> str:
    if "." in filename and not filename.startswith("."):
        base, ext = filename.rsplit(".", 1)
        return f"{base}__{date_str}.{ext}"
    return f"{filename}__{date_str}"


def download_with_browser(
    url: str,
    domain_headers: dict[str, str],
    output_dir: Path,
    date_suffix: str | None,
    user_agent: str,
    wait_ms: int,
) -> bool:
    """Use Playwright to load the URL with auth; capture file response or download. Returns True on success."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("Playwright is required. Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return False

    target_domain = urlparse(url).netloc or ""
    if not target_domain:
        return False

    captured: list[tuple[bytes, str | None]] = []  # (body, content_type)

    our_parsed = urlparse(url)

    def on_response(response):
        try:
            resp_parsed = urlparse(response.url)
            if our_parsed.netloc != resp_parsed.netloc or our_parsed.path != resp_parsed.path:
                return
            if not response.ok:
                return
            ct = response.headers.get("content-type") or ""
            cd = response.headers.get("content-disposition") or ""
            if _looks_like_file_response(ct, cd):
                try:
                    body = response.body()
                    if body and len(body) > 0:
                        captured.append((body, ct))
                except Exception:
                    pass
        except Exception:
            pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=user_agent,
            accept_downloads=True,
        )
        # Inject cookies from auth file
        if "Cookie" in domain_headers:
            cookies = _cookie_header_to_playwright_cookies(domain_headers["Cookie"], target_domain)
            if cookies:
                context.add_cookies(cookies)
        # Optional extra headers (e.g. Authorization)
        extra = {k: v for k, v in domain_headers.items() if k.lower() != "cookie"}
        if extra:
            context.set_extra_http_headers(extra)

        page = context.new_page()
        page.on("response", on_response)

        download_path = None
        try:
            with page.expect_download(timeout=wait_ms + 15000) as dl_info:
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(wait_ms)
            download_path = dl_info.value.path()
        except Exception as e:
            if "Timeout" not in str(type(e).__name__) and "timeout" not in str(e).lower():
                print(f"Navigation error for {url}: {e}", file=sys.stderr)
                browser.close()
                return False
        finally:
            browser.close()

    # Prefer captured binary response over download event
    if captured:
        body = captured[-1][0]
    elif download_path and Path(download_path).exists():
        body = Path(download_path).read_bytes()
    else:
        print(f"No file response captured for {url} (page may have returned only HTML).", file=sys.stderr)
        return False

    filename = deduce_filename(url)
    if date_suffix:
        filename = add_date_suffix(filename, date_suffix)
    out_path = output_dir / filename
    if out_path.exists():
        stem = out_path.stem if out_path.suffix else out_path.name
        ext = out_path.suffix or ""
        n = 1
        while out_path.exists():
            out_path = output_dir / f"{stem}_{n}{ext}"
            n += 1
    out_path.write_bytes(body)
    print(f"Saved: {out_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download URL(s) using a headless browser so JS can run (Playwright)."
    )
    parser.add_argument("urls", nargs="+", help="URL(s) to download")
    parser.add_argument("-o", "--output-dir", default=".", metavar="DIR", help="Output directory")
    parser.add_argument("-d", "--date-suffix", action="store_true", help="Add __YYYY-MM-DD_HHMM before extension")
    parser.add_argument(
        "-w",
        "--wait",
        type=int,
        default=3000,
        metavar="MS",
        help="Ms to wait after load for JS requests (default: 3000)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    date_suffix = None
    if args.date_suffix:
        from datetime import datetime
        date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")
    user_agent = get_user_agent()
    headers_cache: dict[str, dict[str, str]] = {}
    failed_domains: set[str] = set()
    ok = 0

    for url in args.urls:
        url = url.strip()
        if not url:
            continue
        domain = domain_from_url(url)
        if not domain:
            print(f"Invalid URL: {url}", file=sys.stderr)
            continue
        domain_headers = get_domain_headers(domain, headers_cache)
        if not domain_headers:
            if domain not in failed_domains:
                failed_domains.add(domain)
                print(f"No auth file for domain {domain}. Create ~/.auth/site_auth/{domain}", file=sys.stderr)
            continue
        if download_with_browser(url, domain_headers, output_dir, date_suffix, user_agent, args.wait):
            ok += 1

    if failed_domains or ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
