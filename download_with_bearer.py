#!/usr/bin/env python3
"""
Download one or more URLs using Bearer token and/or cookie-based auth.
Per-domain credentials are read from ~/.auth/site_auth/<domain>.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

# Directory under home where per-domain auth files live (filename = domain, ":" → "_")
SITE_AUTH_DIR = os.path.expanduser("~/.auth/site_auth")

# Default User-Agent; overridden by ~/.chrome_agent if that file exists
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36"
)
CHROME_AGENT_FILE = os.path.expanduser("~/.chrome_agent")

# Message when no auth file exists for a domain
NO_TOKEN_MESSAGE = """No auth file found for domain {domain}.
Create: {path}

  Option A — Bearer only:
    bearer_token=<your-token>

  Option B — Cookie (e.g. Artifactory): paste Request Cookies from Chrome into
    {path_raw}
  then run: parse_cookies_to_auth.py {path_raw}

  Option C — Both (Bearer + Cookie) or custom headers (one per line):
    bearer_token=<token>
    Cookie: name1=val1; name2=val2
    X-Custom-Header: value
"""


def get_user_agent() -> str:
    """Return User-Agent string: from ~/.chrome_agent if file exists, else default."""
    path = Path(CHROME_AGENT_FILE)
    if path.is_file():
        return path.read_text().strip() or DEFAULT_USER_AGENT
    return DEFAULT_USER_AGENT


def domain_from_url(url: str) -> str:
    """Return the netloc (host[:port]) for token file lookup. Colons replaced with underscore."""
    netloc = urlparse(url).netloc or ""
    return netloc.replace(":", "_") if netloc else ""


def get_domain_headers(domain: str, headers_cache: dict[str, dict[str, str]]) -> dict[str, str] | None:
    """
    Get request headers for domain from cache or from ~/.auth/site_auth/<domain>.
    File format:
      - bearer_token=<value>  → sets Authorization: Bearer <value>
      - Header-Name: value   → sets that header (e.g. Cookie: ...)
      - Legacy: single line without ":" or "bearer_token=" → Bearer token
    Multiple lines and both bearer_token and Cookie (or other headers) are supported.
    Returns None if no file exists.
    """
    if domain in headers_cache:
        return headers_cache[domain]
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
            # Legacy: single line without ":" or "bearer_token=" → Bearer
            if len(lines) == 1:
                headers["Authorization"] = f"Bearer {line}"
            break
    headers_cache[domain] = headers
    return headers


def deduce_filename(url: str) -> str:
    """
    Derive a safe local filename from the URL.
    Uses the last path segment when it looks like a file; otherwise builds a name from domain + path.
    """
    p = urlparse(url)
    path = unquote(p.path or "").strip("/")
    netloc = p.netloc.replace(":", "_")

    # Last path segment
    segments = [s for s in path.split("/") if s]
    last = segments[-1] if segments else ""

    # Looks like a clear filename: has a known extension or single segment that's not just "api"/"v1"
    if last:
        if "." in last and not last.startswith("."):
            # e.g. report.pdf, data.json
            base, ext = last.rsplit(".", 1)
            if len(ext) <= 5 and base:
                return _sanitize_filename(last)
        if segments and last not in ("api", "v1", "v2", "v3", ""):
            return _sanitize_filename(last)

    # No clear filename: build from domain + path (and optionally a bit of query)
    if path:
        path_slug = _sanitize_filename(path.replace("/", "_"))
        name = f"{netloc}_{path_slug}" if netloc else path_slug
    else:
        name = netloc or "download"

    # Optional: add a hint from query string for APIs
    if p.query:
        q = p.query[:32]
        name += "_" + hashlib.md5(p.query.encode(), usedforsecurity=False).hexdigest()[:8]

    if not re.search(r"\.\w+$", name):
        name += ".html"  # default extension when unclear
    return name


def _sanitize_filename(name: str) -> str:
    """Remove or replace characters unsafe in filenames."""
    name = re.sub(r'[<>:"/\\|?*]', "_", name)
    name = name.strip(". ")
    return name or "download"


def add_date_suffix(filename: str, date_str: str) -> str:
    """Insert __YYYY-MM-DD_HHMM before the last file extension."""
    if "." in filename and not filename.startswith("."):
        base, ext = filename.rsplit(".", 1)
        return f"{base}__{date_str}.{ext}"
    return f"{filename}__{date_str}"


def download_url(
    url: str,
    domain_headers: dict[str, str],
    output_dir: Path,
    date_suffix: str | None,
    user_agent: str,
) -> bool:
    """Download URL using per-domain headers and save to output_dir. Returns True on success."""
    headers = {**domain_headers, "User-Agent": user_agent}
    try:
        resp = requests.get(url, headers=headers, timeout=60)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}", file=sys.stderr)
        return False

    filename = deduce_filename(url)
    if date_suffix:
        filename = add_date_suffix(filename, date_suffix)
    out_path = output_dir / filename

    # Avoid overwriting: if exists, add a numeric suffix
    if out_path.exists():
        stem, ext = (out_path.stem, out_path.suffix) if out_path.suffix else (out_path.name, "")
        n = 1
        while out_path.exists():
            out_path = output_dir / f"{stem}_{n}{ext}"
            n += 1

    out_path.write_bytes(resp.content)
    print(f"Saved: {out_path}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download URL(s) using Bearer and/or cookie auth (see ~/.auth/site_auth/<domain>)."
    )
    parser.add_argument(
        "urls",
        nargs="+",
        help="One or more URLs to download",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        metavar="DIR",
        help="Directory to save downloaded files (default: current directory)",
    )
    parser.add_argument(
        "-d",
        "--date-suffix",
        action="store_true",
        help='Add a date suffix __YYYY-MM-DD_HHMM before the file extension',
    )
    parser.add_argument(
        "--js",
        action="store_true",
        help="Use a headless browser (Playwright) so JavaScript runs; captures the real file if the server returns HTML without JS",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    date_suffix: str | None = None
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
            print(f"Invalid URL (no host): {url}", file=sys.stderr)
            continue
        domain_headers = get_domain_headers(domain, headers_cache)
        if not domain_headers:
            if domain not in failed_domains:
                failed_domains.add(domain)
                auth_path = Path(SITE_AUTH_DIR) / domain
                raw_path = auth_path.parent / f"{domain}.raw.txt"
                print(
                    NO_TOKEN_MESSAGE.format(
                        domain=domain,
                        path=auth_path,
                        path_raw=raw_path,
                    ),
                    file=sys.stderr,
                )
            continue
        if args.js:
            script_dir = Path(__file__).resolve().parent
            helper = script_dir / "download_with_js.py"
            cmd = [sys.executable, str(helper), "-o", str(output_dir)]
            if date_suffix:
                cmd.append("-d")
            cmd.append(url)
            try:
                if subprocess.run(cmd, check=False).returncode == 0:
                    ok += 1
            except Exception as e:
                print(f"JS download failed for {url}: {e}", file=sys.stderr)
        elif download_url(url, domain_headers, output_dir, date_suffix, user_agent):
            ok += 1

    if failed_domains:
        sys.exit(1)
    if ok == 0 and args.urls:
        sys.exit(1)


if __name__ == "__main__":
    main()
