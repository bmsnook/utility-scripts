#!/usr/bin/env python3
"""
Download one or more URLs using Bearer token auth.
Tokens are read from ~/.auth/bearer_tokens/<domain> per URL domain.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, unquote

import requests

# Directory under home where token files are stored (filename = domain, with ":" → "_")
BEARER_TOKENS_DIR = os.path.expanduser("~/.auth/bearer_tokens")

# Message when no token file exists for a domain
NO_TOKEN_MESSAGE = """No bearer token found for domain {domain}.
To add a token:
  1. In Google Chrome, open DevTools (F12 or Cmd+Option+I).
  2. Go to the Network tab and enable "Preserve log".
  3. Log in to the site so the session cookie is set.
  4. Find the request that uses the token and look for "ACCESSTOKEN" in the Cookie
     for the current session, or copy the Bearer token from the request Authorization header.
  5. Save the token in: {path}
     (one line, no "Bearer " prefix needed)
"""


def domain_from_url(url: str) -> str:
    """Return the netloc (host[:port]) for token file lookup. Colons replaced with underscore."""
    netloc = urlparse(url).netloc or ""
    return netloc.replace(":", "_") if netloc else ""


def get_bearer_token(domain: str, token_cache: dict) -> str | None:
    """
    Get bearer token for domain from token_cache or from ~/.auth/bearer_tokens/<domain>.
    Updates token_cache. Returns None if no token file exists.
    """
    if domain in token_cache:
        return token_cache[domain]
    tokens_dir = Path(BEARER_TOKENS_DIR)
    token_file = tokens_dir / domain
    if not token_file.is_file():
        return None
    token = token_file.read_text().strip()
    token_cache[domain] = token
    return token


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
    token: str,
    output_dir: Path,
    date_suffix: str | None,
) -> bool:
    """Download URL with Bearer token and save to output_dir. Returns True on success."""
    headers = {"Authorization": f"Bearer {token}"}
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
        description="Download URL(s) using Bearer token auth (tokens from ~/.auth/bearer_tokens/<domain>)."
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
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    date_suffix: str | None = None
    if args.date_suffix:
        from datetime import datetime
        date_suffix = datetime.now().strftime("%Y-%m-%d_%H%M")

    token_cache: dict[str, str] = {}
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
        token = get_bearer_token(domain, token_cache)
        if not token:
            if domain not in failed_domains:
                failed_domains.add(domain)
                token_path = Path(BEARER_TOKENS_DIR) / domain
                print(NO_TOKEN_MESSAGE.format(domain=domain, path=token_path), file=sys.stderr)
            continue
        if download_url(url, token, output_dir, date_suffix):
            ok += 1

    if failed_domains:
        sys.exit(1)
    if ok == 0 and args.urls:
        sys.exit(1)


if __name__ == "__main__":
    main()
