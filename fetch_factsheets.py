#!/usr/bin/env python3
"""
fetch_factsheets.py — Jupiter Asset Management factsheet downloader
Scrapes jupiteram.com for publicly available fund factsheet PDFs,
downloads new/changed ones into ./factsheets/, and writes funds.json.
"""

import os
import re
import json
import hashlib
import time
import datetime
import sys
from urllib.parse import urljoin, urlparse

try:
    import requests
    from bs4 import BeautifulSoup
except ImportError:
    print("ERROR: Missing dependencies. Run:  pip install -r requirements.txt")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
BASE_URL        = "https://www.jupiteram.com"
SEARCH_URLS     = [
    "https://www.jupiteram.com/uk/en/individual-investors/funds/",
    "https://www.jupiteram.com/uk/en/professional-investors/funds/",
    "https://www.jupiteram.com/globalassets/jupiter/documents/en-gb/factsheets/",
]
FACTSHEET_DIR   = "factsheets"
FUNDS_JSON      = "funds.json"
HASH_CACHE      = os.path.join(FACTSHEET_DIR, ".hashes.json")
REQUEST_DELAY   = 1.2          # seconds between requests — be polite
TIMEOUT         = 20           # seconds per HTTP request
HEADERS         = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_hash_cache() -> dict:
    if os.path.exists(HASH_CACHE):
        try:
            with open(HASH_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_hash_cache(cache: dict):
    with open(HASH_CACHE, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2)


def slugify(name: str) -> str:
    """Convert a fund name to a filename-safe slug."""
    s = name.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s).strip("-")
    return s[:80]


def friendly_name(filename: str) -> str:
    """Best-effort human name from a PDF filename."""
    stem = os.path.splitext(os.path.basename(filename))[0]
    # strip common suffixes
    stem = re.sub(r"[-_](factsheet|fact-sheet|en-gb|en-us|uk|gb).*$", "", stem, flags=re.I)
    stem = re.sub(r"[-_]+", " ", stem)
    # title-case, but keep common acronyms
    words = stem.split()
    skip = {"and", "of", "the", "for", "in", "a", "an"}
    return " ".join(
        w.upper() if len(w) <= 3 and w.lower() not in skip else w.capitalize()
        for w in words
    )


def get_session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def collect_pdf_links(session: requests.Session) -> list[dict]:
    """
    Crawl SEARCH_URLS looking for links to factsheet PDFs.
    Returns a list of {"url": ..., "name": ...} dicts, deduped by URL.
    """
    seen_urls: set[str] = set()
    found: list[dict] = []

    for start_url in SEARCH_URLS:
        print(f"  → Scanning {start_url}")
        try:
            r = session.get(start_url, timeout=TIMEOUT, allow_redirects=True)
            r.raise_for_status()
        except Exception as e:
            print(f"    ⚠  Could not fetch {start_url}: {e}")
            continue

        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href: str = a["href"].strip()
            if not href:
                continue
            # Resolve relative URLs
            full = urljoin(start_url, href)
            # Only keep links that look like factsheet PDFs
            lower = full.lower()
            if not lower.endswith(".pdf"):
                continue
            if "factsheet" not in lower and "fact-sheet" not in lower:
                continue
            if full in seen_urls:
                continue
            seen_urls.add(full)
            # Derive a name from link text or URL
            link_text = a.get_text(strip=True)
            if link_text and len(link_text) > 5:
                name = link_text
            else:
                name = friendly_name(urlparse(full).path)
            found.append({"url": full, "name": name})
            print(f"    ✓ Found: {name}")
        time.sleep(REQUEST_DELAY)

    # Second pass: also scan individual fund pages for deeper PDF links
    # Look for links that contain /funds/ and seem to be fund pages
    fund_page_links: set[str] = set()
    for start_url in SEARCH_URLS[:2]:
        try:
            r = session.get(start_url, timeout=TIMEOUT)
            r.raise_for_status()
        except Exception:
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            full = urljoin(start_url, href)
            parsed = urlparse(full)
            if (
                parsed.netloc in ("www.jupiteram.com", "jupiteram.com")
                and "/funds/" in parsed.path
                and not full.endswith(".pdf")
                and full not in fund_page_links
                and len(parsed.path.split("/")) >= 6  # deep enough to be a fund page
            ):
                fund_page_links.add(full)

    if fund_page_links:
        print(f"\n  → Scanning {len(fund_page_links)} individual fund pages for factsheets…")
        for fund_url in sorted(fund_page_links):
            try:
                r = session.get(fund_url, timeout=TIMEOUT)
                r.raise_for_status()
                soup = BeautifulSoup(r.text, "html.parser")
                for a in soup.find_all("a", href=True):
                    href = a["href"].strip()
                    full = urljoin(fund_url, href)
                    lower = full.lower()
                    if lower.endswith(".pdf") and ("factsheet" in lower or "fact-sheet" in lower):
                        if full not in seen_urls:
                            seen_urls.add(full)
                            name = a.get_text(strip=True) or friendly_name(urlparse(full).path)
                            found.append({"url": full, "name": name})
                            print(f"    ✓ Found: {name}")
                time.sleep(REQUEST_DELAY)
            except Exception as e:
                print(f"    ⚠  {fund_url}: {e}")

    return found


def download_factsheets(session: requests.Session, links: list[dict]) -> list[dict]:
    """
    Download each PDF if new or changed (by SHA-256).
    Returns list of fund records for funds.json.
    """
    os.makedirs(FACTSHEET_DIR, exist_ok=True)
    cache = load_hash_cache()
    today = datetime.date.today().isoformat()
    funds = []
    errors = []

    for item in links:
        url: str = item["url"]
        name: str = item["name"]
        slug = slugify(name)
        filename = slug + "-factsheet.pdf"
        filepath = os.path.join(FACTSHEET_DIR, filename)
        rel_path = FACTSHEET_DIR + "/" + filename

        print(f"\n  [{name}]")
        print(f"    URL: {url}")

        try:
            # Download to memory first to check hash
            r = session.get(url, timeout=TIMEOUT, stream=False)
            r.raise_for_status()
            content_type = r.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and not url.lower().endswith(".pdf"):
                print(f"    ⚠  Skipping — response is not a PDF ({content_type})")
                continue
            data = r.content
            if len(data) < 1000:
                print(f"    ⚠  Skipping — file too small ({len(data)} bytes), likely an error page")
                continue

            new_hash = sha256_of_bytes(data)
            old_hash = cache.get(url)

            if os.path.exists(filepath) and old_hash == new_hash:
                print(f"    ↷  Unchanged — skipping download")
            else:
                action = "Updated" if os.path.exists(filepath) else "Downloaded"
                with open(filepath, "wb") as f:
                    f.write(data)
                cache[url] = new_hash
                print(f"    ✓  {action} ({len(data):,} bytes) → {filepath}")

            funds.append({
                "name": name,
                "file": rel_path,
                "updated": today,
            })
            time.sleep(REQUEST_DELAY)

        except requests.exceptions.HTTPError as e:
            msg = f"HTTP {e.response.status_code} — {url}"
            print(f"    ✗  {msg}")
            errors.append(msg)
        except requests.exceptions.ConnectionError as e:
            msg = f"Connection error — {url}: {e}"
            print(f"    ✗  {msg}")
            errors.append(msg)
        except requests.exceptions.Timeout:
            msg = f"Timeout — {url}"
            print(f"    ✗  {msg}")
            errors.append(msg)
        except Exception as e:
            msg = f"Unexpected error — {url}: {e}"
            print(f"    ✗  {msg}")
            errors.append(msg)

    save_hash_cache(cache)

    if errors:
        print(f"\n  ⚠  {len(errors)} download(s) failed:")
        for e in errors:
            print(f"     • {e}")

    return funds


def merge_with_existing(new_funds: list[dict]) -> list[dict]:
    """
    If funds.json exists, keep entries for files that still exist on disk
    but weren't found in the latest scrape (e.g. manually added PDFs).
    """
    if not os.path.exists(FUNDS_JSON):
        return new_funds

    try:
        with open(FUNDS_JSON, "r", encoding="utf-8") as f:
            existing = json.load(f)
    except Exception:
        return new_funds

    new_files = {f["file"] for f in new_funds}
    extra = [
        e for e in existing
        if e.get("file") not in new_files and os.path.exists(e.get("file", ""))
    ]
    if extra:
        print(f"\n  ℹ  Keeping {len(extra)} manually-added fund(s) from previous funds.json")
    return new_funds + extra


def write_funds_json(funds: list[dict]):
    with open(FUNDS_JSON, "w", encoding="utf-8") as f:
        json.dump(funds, f, indent=2, ensure_ascii=False)
    print(f"\n  ✓  funds.json written ({len(funds)} fund(s))")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    # Change to script directory so relative paths resolve correctly
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    print("=" * 60)
    print("  Jupiter Asset Management — Factsheet Fetcher")
    print("=" * 60)

    session = get_session()

    print("\n[1/3] Scanning Jupiter website for factsheet links…")
    links = collect_pdf_links(session)

    if not links:
        print("\n  ℹ  No factsheet PDF links found via scraping.")
        print("     This may be because the site uses JavaScript rendering.")
        print("     Checking for existing PDFs in ./factsheets/ …")
        # If there are already PDFs on disk (e.g. manually placed), build funds.json from those
        funds = []
        if os.path.isdir(FACTSHEET_DIR):
            today = datetime.date.today().isoformat()
            for fname in sorted(os.listdir(FACTSHEET_DIR)):
                if fname.endswith(".pdf"):
                    funds.append({
                        "name": friendly_name(fname),
                        "file": FACTSHEET_DIR + "/" + fname,
                        "updated": today,
                    })
        if funds:
            print(f"     Found {len(funds)} existing PDF(s) — building funds.json from those.")
            write_funds_json(funds)
        else:
            print("     No PDFs found. Please download fund factsheets manually")
            print(f"     from https://www.jupiteram.com and place them in ./{FACTSHEET_DIR}/")
            # Write an empty funds.json so the app doesn't break
            write_funds_json([])
        print("\nDone.\n")
        return

    print(f"\n  Found {len(links)} factsheet link(s) to process.")

    print("\n[2/3] Downloading new and updated factsheets…")
    funds = download_factsheets(session, links)

    print("\n[3/3] Updating funds.json…")
    funds = merge_with_existing(funds)
    write_funds_json(funds)

    print("\n" + "=" * 60)
    print(f"  Complete. {len(funds)} fund(s) available in funds.json.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
