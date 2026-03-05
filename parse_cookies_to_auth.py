#!/usr/bin/env python3
"""
Parse Chrome DevTools Request Cookies paste into a site auth file.

Reads <domain>.raw.txt (tab-separated paste from Network → Request Cookies),
extracts Name and Value columns, and writes ~/.auth/site_auth/<domain> with
a single "Cookie: name1=value1; name2=value2; ..." line.

Usage:
  parse_cookies_to_auth.py <domain>.raw.txt [<domain2>.raw.txt ...]
  parse_cookies_to_auth.py --all   # process all *.raw.txt in site_auth dir

Expected paste format (Chrome Request Cookies table):
  Name, Value, Domain, Path, Expires / Max-Age, Size, HttpOnly, Secure, SameSite, ...
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Same directory as download_with_bearer.py uses
SITE_AUTH_DIR = os.path.expanduser("~/.auth/site_auth")

# Chrome Request Cookies column headers (order may vary; we look up by name)
COOKIE_HEADERS = ("Name", "Value")


def parse_tsv_cookies(text: str) -> list[tuple[str, str]]:
    """
    Parse tab-separated cookie table; first line = headers.
    Returns list of (name, value) for cookie pairs.
    """
    lines = [ln.rstrip("\r") for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return []
    header_line = lines[0]
    parts = header_line.split("\t")
    try:
        name_idx = parts.index("Name")
        value_idx = parts.index("Value")
    except ValueError:
        # Fallback: first two columns
        name_idx, value_idx = 0, 1
    pairs = []
    for line in lines[1:]:
        cols = line.split("\t")
        if len(cols) > max(name_idx, value_idx):
            name = cols[name_idx].strip()
            value = cols[value_idx].strip()
            if name:
                pairs.append((name, value))
    return pairs


def build_cookie_header(pairs: list[tuple[str, str]]) -> str:
    """Build Cookie header value from (name, value) pairs."""
    return "; ".join(f"{name}={value}" for name, value in pairs)


def domain_from_raw_filename(path: Path) -> str | None:
    """Return domain from '<domain>.raw.txt' filename, or None."""
    name = path.name
    if name.endswith(".raw.txt"):
        return name[: -len(".raw.txt")].strip() or None
    return None


def process_raw_file(raw_path: Path, out_dir: Path, dry_run: bool) -> bool:
    """Parse raw cookie file and write <domain> auth file. Returns True on success."""
    domain = domain_from_raw_filename(raw_path)
    if not domain:
        print(f"Skip (not *.raw.txt): {raw_path}", file=sys.stderr)
        return False
    if not raw_path.is_file():
        print(f"Not a file: {raw_path}", file=sys.stderr)
        return False
    text = raw_path.read_text()
    pairs = parse_tsv_cookies(text)
    if not pairs:
        print(f"No cookies parsed from {raw_path}", file=sys.stderr)
        return False
    cookie_value = build_cookie_header(pairs)
    out_file = out_dir / domain
    line = f"Cookie: {cookie_value}\n"
    if dry_run:
        print(f"Would write {len(pairs)} cookie(s) to {out_file}")
        return True
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file.write_text(line)
    print(f"Wrote {out_file} ({len(pairs)} cookie(s))")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse Chrome Request Cookies paste (.raw.txt) into site auth file(s)."
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Paths to <domain>.raw.txt files",
    )
    parser.add_argument(
        "-a",
        "--all",
        action="store_true",
        help=f"Process all *.raw.txt under {SITE_AUTH_DIR}",
    )
    parser.add_argument(
        "-d",
        "--auth-dir",
        default=SITE_AUTH_DIR,
        metavar="DIR",
        help=f"Auth directory (default: {SITE_AUTH_DIR})",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Do not write files; show what would be done",
    )
    args = parser.parse_args()

    out_dir = Path(args.auth_dir).expanduser().resolve()

    if args.all:
        if not out_dir.is_dir():
            print(f"Auth dir does not exist: {out_dir}", file=sys.stderr)
            sys.exit(1)
        files = list(out_dir.glob("*.raw.txt"))
        if not files:
            print(f"No *.raw.txt files in {out_dir}", file=sys.stderr)
            sys.exit(1)
    else:
        if not args.files:
            parser.error("Provide one or more .raw.txt files, or use --all")
        files = [Path(p).expanduser().resolve() for p in args.files]

    ok = 0
    for f in files:
        if process_raw_file(f, out_dir, args.dry_run):
            ok += 1
    if ok == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
