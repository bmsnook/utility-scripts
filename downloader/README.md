# Downloader utilities

Scripts to download URLs using per-domain authentication (Bearer tokens and/or cookies). Credentials are read from `~/.auth/site_auth/<domain>` so you can reuse the same auth for multiple URLs on the same host.

## Auth storage

- **Directory:** `~/.auth/site_auth/`
- **Per domain:** one file per host, named by domain (e.g. `example.com` or `api.example.com_443` for a non-default port).
- **Formats:**
  - **Bearer only:** a single line `bearer_token=<your-token>`
  - **Cookie-based:** a line `Cookie: name1=value1; name2=value2`
  - **Both / custom:** multiple lines; any `Header-Name: value` line is sent as that HTTP header.

User-Agent can be overridden by putting a single line in `~/.chrome_agent`; otherwise a default Chrome-like UA is used.

---

## Scripts

### download_with_auth.py

Main entry point. Downloads one or more URLs using credentials from `~/.auth/site_auth/<domain>`.

**Usage:**

```bash
./download_with_auth.py <url> [<url> ...] [-o DIR] [-d] [--js]
```

| Option | Description |
|--------|-------------|
| `url` | One or more URLs to download (positional). |
| `-o`, `--output-dir` | Directory to save files (default: current directory). |
| `-d`, `--date-suffix` | Add `__YYYY-MM-DD_HHMM` before the file extension. |
| `--js` | Use a headless browser so JavaScript runs; use when the server returns an HTML shell that requires JS to serve or reveal the real file. |

- Output filenames are derived from the URL path; if the path is ambiguous (e.g. API endpoints), a name is built from domain and path. Existing files get a numeric suffix to avoid overwriting.

---

### parse_cookies_to_auth.py

Turns a paste of the browser’s **Request Cookies** table (e.g. from DevTools → Network → request → Cookies) into a `Cookie: ...` auth line and writes it to the corresponding domain file.

**Usage:**

```bash
./parse_cookies_to_auth.py <domain>.raw.txt [<domain2>.raw.txt ...]
./parse_cookies_to_auth.py --all
```

- **Input:** Files named `<domain>.raw.txt` containing tab- or space-separated cookie rows. No header row is expected; column order is defined by `REQUEST_COOKIES_COLUMNS` in the script (edit if the browser table layout changes).
- **Output:** Writes `~/.auth/site_auth/<domain>` with a single `Cookie: name=value; ...` line.
- **Options:** `-a` / `--all` processes every `*.raw.txt` in the auth directory; `-d DIR` overrides the auth directory; `-n` / `--dry-run` only reports what would be written.

**Workflow:** Copy the cookie table from the browser into `<domain>.raw.txt`, then run the script so `download_with_auth.py` can use the generated auth file.

---

### download_with_js.py

Downloads a URL in a headless Chromium (Playwright) so the page’s JavaScript runs. Use when the server first returns HTML (e.g. “enable JavaScript”) and the real file is only delivered or revealed after JS runs.

**Usage:**

```bash
./download_with_js.py <url> [<url> ...] [-o DIR] [-d] [-w MS]
```

| Option | Description |
|--------|-------------|
| `-o`, `--output-dir` | Output directory (default: current directory). |
| `-d`, `--date-suffix` | Add `__YYYY-MM-DD_HHMM` before the file extension. |
| `-w`, `--wait` | Milliseconds to wait after load for JS-initiated requests (default: 3000). |

- Uses the same auth as the main script (`~/.auth/site_auth/<domain>`). Captures file-like responses (e.g. `application/octet-stream`) for the same URL path, or a browser download event if the page triggers one.
- **Dependency:** `pip install playwright` and `playwright install chromium`. You can also invoke this script via `download_with_auth.py --js`.

---

## Requirements

- Python 3 with `requests`. For `download_with_js.py`, install Playwright and Chromium as above.
- Auth directory: `mkdir -p ~/.auth/site_auth` and create or generate per-domain auth files as described.
