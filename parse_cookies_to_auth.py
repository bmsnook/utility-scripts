#!/usr/bin/env python3
"""
Parse Chrome DevTools Request Cookies paste into a site auth file.

Reads <domain>.raw.txt (tab-separated paste from Network → Request Cookies).
The paste typically has no header row (Chrome doesn't let you copy it); column
order is defined by REQUEST_COOKIES_COLUMNS below. Edit that list if Chrome
changes the table order or column names.

Usage:
  parse_cookies_to_auth.py <domain>.raw.txt [<domain2>.raw.txt ...]
  parse_cookies_to_auth.py --all   # process all *.raw.txt in site_auth dir
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Same directory as download_with_bearer.py uses
SITE_AUTH_DIR = os.path.expanduser("~/.auth/site_auth")

# Chrome Request Cookies table column order (left to right). Edit if Chrome changes.
# Only "Name" and "Value" are used; others are for correct column indexing.
REQUEST_COOKIES_COLUMNS = [
    "Name",
    "Value",
    "Domain",
    "Path",
    "Expires / Max-Age",
    "Size",
    "HttpOnly",
    "Secure",
    "SameSite",
    "Partition Key Site",
    "Cross Site",
    "Priority",
]

# Indices for cookie name/value (derived from REQUEST_COOKIES_COLUMNS)
NAME_COL = REQUEST_COOKIES_COLUMNS.index("Name") if "Name" in REQUEST_COOKIES_COLUMNS else 0
VALUE_COL = REQUEST_COOKIES_COLUMNS.index("Value") if "Value" in REQUEST_COOKIES_COLUMNS else 1


def parse_tsv_cookies(text: str) -> list[tuple[str, str]]:
    """
    Parse tab-separated cookie table. No header row is expected; column order
    is given by REQUEST_COOKIES_COLUMNS (Name at NAME_COL, Value at VALUE_COL).
    Returns list of (name, value) for cookie pairs.
    """
    lines = [ln.rstrip("\r") for ln in text.strip().splitlines() if ln.strip()]
    pairs = []
    need = max(NAME_COL, VALUE_COL) + 1
    for line in lines:
        cols = line.split("\t")
        if len(cols) >= need:
            name = cols[NAME_COL].strip()
            value = cols[VALUE_COL].strip()
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
