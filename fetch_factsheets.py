#!/usr/bin/env python3
"""
fetch_factsheets.py — Jupiter Asset Management fund scraper (Playwright edition)
Uses a headless Chromium browser to fully render JavaScript before extracting data.

Usage:
    python fetch_factsheets.py
    playwright install chromium   # first time only
"""

import os
import re
import json
import hashlib
import datetime
import sys
import time

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    print("ERROR: Playwright not installed.")
    print("  pip install -r requirements.txt")
    print("  playwright install chromium")
    sys.exit(1)

# ── Config ────────────────────────────────────────────────────────────────────
FUND_CENTRE_URL = "https://www.jupiteram.com/uk/en/individual/fund-centre/"
FACTSHEETS_DIR  = "factsheets"
FUNDS_JSON      = "funds.json"
PAGE_TIMEOUT    = 30_000   # ms — general element wait
NAV_TIMEOUT     = 60_000   # ms — full page navigation
TAB_WAIT        = 3_000    # ms — wait after clicking a tab


# ── Utilities ─────────────────────────────────────────────────────────────────

def today():
    return datetime.date.today().isoformat()


def clean(s):
    """Normalise whitespace in a string."""
    return re.sub(r"\s+", " ", str(s or "")).strip()


def slugify(s):
    s = re.sub(r"[^\w\s-]", "", s.lower())
    return re.sub(r"[\s_]+", "-", s).strip("-")[:80]


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def extract_text(page, selectors):
    """Try each selector in order; return the first non-empty inner text."""
    for sel in selectors:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                t = clean(el.inner_text(timeout=3000))
                if t:
                    return t
        except Exception:
            pass
    return ""


def extract_table(page, selectors):
    """
    Try each selector; return the first table found as a list of row lists.
    Each row is a list of cell strings.
    """
    for sel in selectors:
        try:
            table = page.locator(sel).first
            if table.count() == 0:
                continue
            rows = []
            for tr in table.locator("tr").all():
                cells = [clean(td.inner_text()) for td in tr.locator("td, th").all()]
                if any(cells):
                    rows.append(cells)
            if rows:
                return rows
        except Exception:
            pass
    return []


def rows_to_dicts(rows):
    """Convert a table (list of row lists) to a list of dicts using the first row as headers."""
    if len(rows) < 2:
        return []
    headers = rows[0]
    result = []
    for row in rows[1:]:
        entry = {}
        for i, h in enumerate(headers):
            if i < len(row) and h:
                entry[h] = row[i]
        if entry:
            result.append(entry)
    return result


def try_click_tab(page, tab_name):
    """
    Attempt to click a named tab using several selector strategies.
    Returns True if a tab was found and clicked.
    """
    candidates = [
        f"[role='tab']:has-text('{tab_name}')",
        f"button:has-text('{tab_name}')",
        f"a:has-text('{tab_name}')",
        f"li > a:has-text('{tab_name}')",
        f"[class*='tab']:has-text('{tab_name}')",
        f"[class*='nav']:has-text('{tab_name}')",
        f"[data-tab*='{tab_name.lower()}']",
    ]
    for sel in candidates:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible(timeout=2000):
                el.click()
                page.wait_for_timeout(TAB_WAIT)
                return True
        except Exception:
            pass
    return False


def dismiss_overlays(page):
    """
    Dismiss cookie banners, consent screens, and investor-type selectors.
    Called on the fund centre page and again after each navigation.
    """
    overlay_selectors = [
        # Generic cookie/consent buttons
        "button:has-text('Accept all')",
        "button:has-text('Accept All')",
        "button:has-text('Accept cookies')",
        "button:has-text('Accept Cookies')",
        "button:has-text('I accept')",
        "button:has-text('Accept')",
        "button:has-text('Agree')",
        "button:has-text('Confirm')",
        "button:has-text('I understand')",
        "button:has-text('Got it')",
        "[id*='accept'][type='button']",
        "[class*='cookie-accept']",
        "[class*='consent'] button",
        # Jupiter investor-type gate
        "button:has-text('Individual investor')",
        "button:has-text('Private investor')",
        "a:has-text('Individual investor')",
        "a:has-text('Private investor')",
        "button:has-text('I am an individual investor')",
        "button:has-text('Continue as')",
        # Generic modal dismissals
        "button:has-text('Continue')",
        "button:has-text('Proceed')",
        "[class*='modal'] button:has-text('Close')",
        "[aria-label='Close']",
    ]
    for sel in overlay_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click()
                page.wait_for_timeout(800)
        except Exception:
            pass


# ── Step 1: Fund list ─────────────────────────────────────────────────────────

def get_fund_list(page):
    """
    Navigate to the fund centre, wait for the fund list to render,
    and return a list of {name, url} dicts.
    """
    print(f"\n  Navigating to {FUND_CENTRE_URL} …")
    try:
        page.goto(FUND_CENTRE_URL, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
    except Exception as e:
        print(f"  ✗ Navigation failed: {e}")
        return []

    page.wait_for_timeout(3000)
    dismiss_overlays(page)
    page.wait_for_timeout(2000)
    dismiss_overlays(page)  # layered popups

    # Scroll to trigger any lazy-loaded content
    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
    page.wait_for_timeout(2000)
    page.evaluate("window.scrollTo(0, 0)")
    page.wait_for_timeout(1000)

    # Candidate selectors for fund links
    fund_link_patterns = [
        "a[href*='/fund/']",
        "a[href*='fund-centre/']",
        "[class*='fund-card'] a",
        "[class*='fund-list'] a[href]",
        "[class*='fund-item'] a[href]",
        "[class*='fund-name'] a[href]",
        "[class*='fund-tile'] a[href]",
        "article a[href*='fund']",
        "[class*='card'] a[href*='fund']",
    ]

    print("  Waiting for fund cards to appear…")
    # Wait up to 20s for any fund link pattern to appear
    found_any = False
    deadline = time.time() + 20
    while time.time() < deadline and not found_any:
        for sel in fund_link_patterns:
            try:
                if page.locator(sel).count() > 0:
                    found_any = True
                    break
            except Exception:
                pass
        if not found_any:
            time.sleep(0.8)

    if not found_any:
        print("  ⚠  No fund links detected after waiting. Page may require additional interaction.")
        # Last attempt: dump all <a href> links containing 'fund' for diagnostics
        try:
            all_links = page.locator("a[href*='fund']").all()
            print(f"  Diagnostic: found {len(all_links)} link(s) containing 'fund' in href")
        except Exception:
            pass

    # Collect all matching links, deduped by URL
    seen_urls = set()
    funds = []

    for sel in fund_link_patterns:
        try:
            for link in page.locator(sel).all():
                try:
                    href = link.get_attribute("href") or ""
                    name = clean(link.inner_text())
                    if not href or not name or len(name) < 3:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.jupiteram.com" + href
                    # Skip non-fund pages and anchor links
                    if href in seen_urls or "#" == href[-1]:
                        continue
                    # Filter out obvious non-fund pages
                    skip_terms = ["/contact", "/about", "/news", "/legal", "/privacy",
                                  "/search", "/login", "/register", "mailto:", "javascript:"]
                    if any(t in href.lower() for t in skip_terms):
                        continue
                    seen_urls.add(href)
                    funds.append({"name": name, "url": href})
                except Exception:
                    pass
        except Exception:
            pass

    # Deduplicate by name (keep first occurrence)
    seen_names = set()
    unique_funds = []
    for f in funds:
        if f["name"] not in seen_names:
            seen_names.add(f["name"])
            unique_funds.append(f)

    print(f"  Found {len(unique_funds)} fund(s).")
    return unique_funds


# ── Step 2a: Overview tab ─────────────────────────────────────────────────────

def extract_overview(page):
    """Extract all key fund metadata from the overview/details section."""
    data = {}

    # Investment objective — usually a longer paragraph
    for sel in [
        "[class*='objective']",
        "[class*='investment-objective']",
        "[class*='fund-objective']",
        "section:has(h2:has-text('Objective')) p",
        "section:has(h2:has-text('Investment')) p",
        "*:has-text('The Fund aims')",
        "*:has-text('The fund aims')",
        "*:has-text('aims to')",
    ]:
        try:
            el = page.locator(sel).first
            if el.count() > 0:
                t = clean(el.inner_text())
                if len(t) > 40:
                    data["investment_objective"] = t
                    break
        except Exception:
            pass

    # Structured field extraction: try dt/dd pairs first
    try:
        dts = page.locator("dt").all()
        dds = page.locator("dd").all()
        for dt, dd in zip(dts, dds):
            k = clean(dt.inner_text()).rstrip(":")
            v = clean(dd.inner_text())
            if k and v:
                data[k] = v
    except Exception:
        pass

    # Field-specific fallbacks with known label names
    field_map = {
        "fund_name":         ["h1", "[class*='fund-name'] h1", "[class*='fund-title']"],
        "isin":              ["[class*='isin']", "dt:has-text('ISIN') + dd"],
        "share_class":       ["[class*='share-class']", "dt:has-text('Share class') + dd"],
        "fund_size":         ["dt:has-text('Fund size') + dd", "dt:has-text('Net assets') + dd",
                              "dt:has-text('AUM') + dd", "[class*='fund-size']"],
        "launch_date":       ["dt:has-text('Launch date') + dd", "dt:has-text('Inception date') + dd"],
        "base_currency":     ["dt:has-text('Base currency') + dd", "dt:has-text('Currency') + dd"],
        "manager":           ["dt:has-text('Fund manager') + dd", "dt:has-text('Manager') + dd",
                              "[class*='fund-manager']", "[class*='manager-name']"],
        "benchmark":         ["dt:has-text('Benchmark') + dd", "dt:has-text('Index') + dd",
                              "[class*='benchmark']"],
        "risk_profile":      ["dt:has-text('Risk and reward') + dd", "dt:has-text('Risk profile') + dd",
                              "dt:has-text('SRRI') + dd", "[class*='risk-rating']", "[class*='srri']"],
        "domicile":          ["dt:has-text('Domicile') + dd", "dt:has-text('Fund domicile') + dd"],
        "legal_structure":   ["dt:has-text('Legal structure') + dd", "dt:has-text('Structure') + dd",
                              "dt:has-text('Fund type') + dd"],
        "ocf":               ["dt:has-text('Ongoing charge') + dd", "dt:has-text('OCF') + dd",
                              "dt:has-text('Total expense') + dd", "dt:has-text('TER') + dd"],
        "min_investment":    ["dt:has-text('Minimum') + dd", "dt:has-text('Min. investment') + dd"],
        "dealing_frequency": ["dt:has-text('Dealing frequency') + dd", "dt:has-text('Dealing') + dd"],
        "cut_off_time":      ["dt:has-text('Cut-off') + dd", "dt:has-text('Dealing cut') + dd"],
        "isa_eligible":      ["dt:has-text('ISA') + dd", "[class*='isa']"],
    }

    for field, selectors in field_map.items():
        if field not in data:
            val = extract_text(page, selectors)
            if val:
                data[field] = val

    # Normalise ISIN — must be uppercase alphanumeric, 12 chars
    raw_isin = (
        data.get("isin") or data.get("ISIN") or
        data.get("ISIN code") or data.get("Isin") or ""
    )
    isin = re.sub(r"[^A-Z0-9]", "", raw_isin.upper())
    if isin:
        data["isin"] = isin

    # Fund name fallback from h1
    if "fund_name" not in data:
        try:
            h1 = page.locator("h1").first
            if h1.count() > 0:
                data["fund_name"] = clean(h1.inner_text())
        except Exception:
            pass

    return data


# ── Step 2b: Performance tab ──────────────────────────────────────────────────

def extract_performance(page):
    """
    Extract performance data from the Performance tab.
    Tries tables first, then looks for data embedded in scripts.
    """
    perf = {
        "periods":         {"1yr": {}, "3yr": {}, "5yr": {}, "10yr": {}},
        "discrete_annual": [],
        "cumulative":      [],
        "tables":          [],
    }

    # Collect all tables on the page
    all_table_sels = [
        "[class*='performance'] table",
        "[class*='returns'] table",
        "[class*='discrete'] table",
        "[class*='cumulative'] table",
        "[class*='annual'] table",
        "section:has(h2:has-text('Performance')) table",
        "section:has(h3:has-text('Performance')) table",
        "table:has(th:has-text('1 year'))",
        "table:has(th:has-text('3 year'))",
        "table:has(th:has-text('5 year'))",
        "table:has(th:has-text('Year'))",
        "table:has(th:has-text('Return'))",
        "table",
    ]

    seen_tables = set()
    for sel in all_table_sels:
        rows = extract_table(page, [sel])
        if not rows:
            continue
        sig = str(rows[:2])  # signature to deduplicate
        if sig in seen_tables:
            continue
        seen_tables.add(sig)
        perf["tables"].append({"selector": sel, "rows": rows})

        # Try to parse as discrete annual performance
        headers = [h.lower() for h in rows[0]] if rows else []
        if any(w in " ".join(headers) for w in ["year", "12 month", "annual", "discrete"]):
            dicts = rows_to_dicts(rows)
            if dicts and not perf["discrete_annual"]:
                perf["discrete_annual"] = dicts

        # Try to parse as cumulative performance
        if any(w in " ".join(headers) for w in ["cumulative", "since launch", "inception"]):
            dicts = rows_to_dicts(rows)
            if dicts and not perf["cumulative"]:
                perf["cumulative"] = dicts

    # Try to intercept JavaScript data (chart data often in window object or script tags)
    try:
        # Check for common chart data patterns in inline scripts
        scripts = page.locator("script:not([src])").all()
        for script in scripts:
            try:
                content = script.inner_html()
            except Exception:
                continue
            if len(content) < 50:
                continue
            lower = content.lower()
            if not any(w in lower for w in ["performance", "return", "fund", "benchmark"]):
                continue

            # Look for date/value arrays
            for period in ["1yr", "3yr", "5yr", "10yr", "1y", "3y", "5y", "10y"]:
                pattern = rf'"{period}".*?\[.*?\]'
                matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
                if matches:
                    key = period.replace("y", "yr") if not period.endswith("yr") else period
                    if key in perf["periods"]:
                        perf["periods"][key]["_raw"] = matches[0][:500]

            # Look for JSON arrays of {date, value} objects
            json_arrays = re.findall(r'\[\s*\{[^]]{0,2000}\}\s*\]', content, re.DOTALL)
            for arr_str in json_arrays[:5]:
                try:
                    arr = json.loads(arr_str)
                    if isinstance(arr, list) and arr and isinstance(arr[0], dict):
                        keys = set(arr[0].keys())
                        if keys & {"date", "x", "Date", "X"}:
                            perf["periods"].setdefault("_raw_series", []).append(arr[:5])
                except Exception:
                    pass
    except Exception:
        pass

    return perf


# ── Step 2c: Portfolio tab ────────────────────────────────────────────────────

def extract_portfolio(page):
    """Extract holdings and allocation data from the Portfolio tab."""
    portfolio = {
        "total_holdings": "",
        "holdings":       [],
        "geographic":     [],
        "sector":         [],
        "asset_class":    [],
    }

    # Total number of holdings
    portfolio["total_holdings"] = extract_text(page, [
        "dt:has-text('Number of holdings') + dd",
        "dt:has-text('Holdings') + dd",
        "[class*='total-holdings']",
        "[class*='number-of-holdings']",
        "*:has-text('Number of holdings')",
    ])

    # Top 10 holdings
    holding_rows = extract_table(page, [
        "[class*='top-holding'] table",
        "[class*='holdings'] table",
        "[class*='holding-list'] table",
        "table:has(th:has-text('Holding'))",
        "table:has(th:has-text('Stock'))",
        "table:has(th:has-text('Security'))",
        "table:has(th:has-text('Company'))",
        "table:has(th:has-text('Name'))",
        "[class*='portfolio'] table",
    ])
    if len(holding_rows) >= 2:
        portfolio["holdings"] = rows_to_dicts(holding_rows)[:10]

    # Geographic allocation
    geo_rows = extract_table(page, [
        "[class*='geographic'] table",
        "[class*='geography'] table",
        "[class*='country'] table",
        "[class*='region'] table",
        "table:has(th:has-text('Country'))",
        "table:has(th:has-text('Region'))",
        "table:has(th:has-text('Geography'))",
    ])
    if len(geo_rows) >= 2:
        portfolio["geographic"] = rows_to_dicts(geo_rows)

    # Sector allocation
    sector_rows = extract_table(page, [
        "[class*='sector'] table",
        "[class*='industry'] table",
        "table:has(th:has-text('Sector'))",
        "table:has(th:has-text('Industry'))",
    ])
    if len(sector_rows) >= 2:
        portfolio["sector"] = rows_to_dicts(sector_rows)

    # Asset class allocation
    asset_rows = extract_table(page, [
        "[class*='asset-class'] table",
        "[class*='asset-type'] table",
        "[class*='asset-allocation'] table",
        "table:has(th:has-text('Asset class'))",
        "table:has(th:has-text('Asset type'))",
        "table:has(th:has-text('Asset'))",
    ])
    if len(asset_rows) >= 2:
        portfolio["asset_class"] = rows_to_dicts(asset_rows)

    return portfolio


# ── Step 2d: Documents tab ────────────────────────────────────────────────────

def extract_documents(page):
    """Find PDF download URLs for factsheet, KIID/KID, and prospectus."""
    docs = {
        "factsheet":  None,
        "kiid":       None,
        "kid":        None,
        "prospectus": None,
        "other":      [],
    }

    pdf_selectors = [
        "a[href$='.pdf']",
        "a[href*='.pdf']",
        "[class*='document'] a[href]",
        "[class*='download'] a[href]",
        "[class*='literature'] a[href]",
        "[class*='doc-list'] a[href]",
        "[class*='factsheet'] a[href]",
    ]

    for sel in pdf_selectors:
        try:
            for link in page.locator(sel).all():
                try:
                    href = (link.get_attribute("href") or "").strip()
                    label = clean(link.inner_text()).lower()
                    aria  = (link.get_attribute("aria-label") or "").lower()
                    title = (link.get_attribute("title") or "").lower()
                    combined = label + " " + aria + " " + title + " " + href.lower()

                    if not href:
                        continue
                    if not href.startswith("http"):
                        href = "https://www.jupiteram.com" + href

                    if "factsheet" in combined or "fact sheet" in combined or "fact-sheet" in combined:
                        docs["factsheet"] = docs["factsheet"] or href
                    elif "kiid" in combined:
                        docs["kiid"] = docs["kiid"] or href
                    elif re.search(r'\bkid\b', combined):
                        docs["kid"] = docs["kid"] or href
                    elif "prospectus" in combined:
                        docs["prospectus"] = docs["prospectus"] or href
                    elif href.endswith(".pdf") and href not in docs["other"]:
                        docs["other"].append(href)
                except Exception:
                    pass
        except Exception:
            pass

    return docs


# ── Step 3: Download PDF ──────────────────────────────────────────────────────

def download_pdf(url, dest_path, context):
    """
    Download a PDF using the Playwright browser context so cookies are preserved.
    Returns ("ok"|"unchanged"|"error", message).
    """
    try:
        response = context.request.get(url, timeout=30_000)
        if response.status != 200:
            return "error", f"HTTP {response.status}"
        data = response.body()
        if len(data) < 500:
            return "error", f"Response too small ({len(data)} bytes) — likely an error page"
        if not data[:4] == b"%PDF":
            return "error", "Response is not a PDF"

        new_hash = sha256_bytes(data)
        if os.path.exists(dest_path) and sha256_file(dest_path) == new_hash:
            return "unchanged", ""

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        with open(dest_path, "wb") as f:
            f.write(data)
        return "ok", f"{len(data):,} bytes"
    except Exception as e:
        return "error", str(e)


# ── Per-fund orchestration ────────────────────────────────────────────────────

def process_fund(page, context, fund_info, stats):
    """
    Visit one fund page, extract all tabs, download PDF, save JSON files.
    Returns a funds.json entry dict, or None on total failure.
    """
    name = fund_info["name"]
    url  = fund_info["url"]
    print(f"\n  ── {name}")
    print(f"     {url}")

    # Navigate to fund page
    try:
        page.goto(url, timeout=NAV_TIMEOUT, wait_until="domcontentloaded")
        page.wait_for_timeout(2500)
        dismiss_overlays(page)
        page.wait_for_timeout(1500)
    except Exception as e:
        msg = f"{name}: page load failed — {e}"
        print(f"     ✗ {msg}")
        stats["errors"].append(msg)
        return None

    result = {"overview": {}, "performance": {}, "portfolio": {}, "documents": {}}

    # ── Overview ──────────────────────────────────────────────────────────────
    try:
        try_click_tab(page, "Overview")
        page.wait_for_timeout(1500)
        result["overview"] = extract_overview(page)
    except Exception as e:
        stats["errors"].append(f"{name}: overview — {e}")
        print(f"     ⚠  Overview failed: {e}")

    # Resolve ISIN and create fund directory
    isin = result["overview"].get("isin", "")
    isin = re.sub(r"[^A-Z0-9]", "", isin.upper())
    folder_name = isin if isin else slugify(name)
    fund_dir = os.path.join(FACTSHEETS_DIR, folder_name)
    os.makedirs(fund_dir, exist_ok=True)

    isin_str = f" (ISIN: {isin})" if isin else " (ISIN not found)"
    print(f"     ✓ Overview{isin_str}")

    # ── Performance ───────────────────────────────────────────────────────────
    try:
        clicked = try_click_tab(page, "Performance")
        if clicked:
            page.wait_for_timeout(TAB_WAIT)  # Charts take longer
            result["performance"] = extract_performance(page)
            n_tables   = len(result["performance"].get("tables", []))
            n_discrete = len(result["performance"].get("discrete_annual", []))
            print(f"     ✓ Performance — {n_tables} table(s), {n_discrete} annual row(s)")
        else:
            print("     ⚠  Performance tab not found")
    except Exception as e:
        stats["errors"].append(f"{name}: performance — {e}")
        print(f"     ⚠  Performance failed: {e}")

    # ── Portfolio ─────────────────────────────────────────────────────────────
    try:
        clicked = try_click_tab(page, "Portfolio")
        if clicked:
            page.wait_for_timeout(TAB_WAIT)
            result["portfolio"] = extract_portfolio(page)
            n_holdings = len(result["portfolio"].get("holdings", []))
            print(f"     ✓ Portfolio — {n_holdings} holding(s)")
        else:
            print("     ⚠  Portfolio tab not found")
    except Exception as e:
        stats["errors"].append(f"{name}: portfolio — {e}")
        print(f"     ⚠  Portfolio failed: {e}")

    # ── Documents ─────────────────────────────────────────────────────────────
    try:
        clicked = try_click_tab(page, "Documents")
        if clicked:
            page.wait_for_timeout(2000)
        # Always try to extract doc links whether tab was found or not
        result["documents"] = extract_documents(page)
        factsheet_url = result["documents"].get("factsheet")
        print(f"     ✓ Documents — factsheet: {factsheet_url or 'not found'}")
    except Exception as e:
        stats["errors"].append(f"{name}: documents — {e}")
        print(f"     ⚠  Documents failed: {e}")

    # ── Download factsheet ────────────────────────────────────────────────────
    factsheet_url  = result["documents"].get("factsheet")
    factsheet_path = os.path.join(fund_dir, "factsheet.pdf")
    has_pdf = os.path.exists(factsheet_path)  # may already be there from a prior run

    if factsheet_url:
        status, msg = download_pdf(factsheet_url, factsheet_path, context)
        if status == "ok":
            print(f"     ✓ PDF downloaded ({msg})")
            stats["downloaded"] += 1
            has_pdf = True
        elif status == "unchanged":
            print("     ↷  PDF unchanged — skipped")
            has_pdf = True
        else:
            print(f"     ✗ PDF download failed: {msg}")
            stats["errors"].append(f"{name}: PDF — {msg}")
    else:
        if not has_pdf:
            print("     ⚠  No factsheet URL found and no existing PDF")

    # ── Save structured JSON ──────────────────────────────────────────────────
    fund_data = {
        "fund_name":  name,
        "isin":       isin,
        "source_url": url,
        "updated":    today(),
        **{k: v for k, v in result["overview"].items() if k != "isin"},
        "portfolio":  result["portfolio"],
    }

    perf_data = {
        "fund_name":       name,
        "isin":            isin,
        "updated":         today(),
        "periods":         result["performance"].get("periods", {"1yr": {}, "3yr": {}, "5yr": {}, "10yr": {}}),
        "discrete_annual": result["performance"].get("discrete_annual", []),
        "cumulative":      result["performance"].get("cumulative", []),
        "tables":          result["performance"].get("tables", []),
    }

    with open(os.path.join(fund_dir, "fund_data.json"), "w", encoding="utf-8") as f:
        json.dump(fund_data, f, indent=2, ensure_ascii=False)
    with open(os.path.join(fund_dir, "performance_data.json"), "w", encoding="utf-8") as f:
        json.dump(perf_data, f, indent=2, ensure_ascii=False)

    has_perf = bool(
        result["performance"].get("tables") or
        result["performance"].get("discrete_annual") or
        result["performance"].get("cumulative")
    )
    has_port = bool(
        result["portfolio"].get("holdings") or
        result["portfolio"].get("geographic")
    )

    stats["processed"] += 1

    return {
        "name":                 name,
        "isin":                 isin,
        "share_class":          result["overview"].get("share_class") or result["overview"].get("Share class", ""),
        "folder":               fund_dir.replace("\\", "/"),
        "factsheet":            factsheet_path.replace("\\", "/") if has_pdf else "",
        "has_performance_data": has_perf,
        "has_portfolio_data":   has_port,
        "updated":              today(),
    }


# ── Fallback: scan existing PDFs ──────────────────────────────────────────────

def build_from_existing():
    """
    If scraping found nothing, scan ./factsheets/ for any PDFs already present
    (e.g. manually downloaded) and build funds.json from those.
    """
    funds = []
    if not os.path.isdir(FACTSHEETS_DIR):
        return funds

    today_str = today()

    for entry in sorted(os.scandir(FACTSHEETS_DIR), key=lambda e: e.name):
        if entry.is_dir() and not entry.name.startswith("."):
            pdf = os.path.join(entry.path, "factsheet.pdf")
            if os.path.isfile(pdf):
                isin = entry.name if re.match(r"^[A-Z]{2}[A-Z0-9]{10}$", entry.name) else ""
                # Try to load existing fund_data.json for the name
                fund_data_path = os.path.join(entry.path, "fund_data.json")
                name = entry.name
                if os.path.isfile(fund_data_path):
                    try:
                        with open(fund_data_path, encoding="utf-8") as f:
                            d = json.load(f)
                        name = d.get("fund_name") or name
                    except Exception:
                        pass
                funds.append({
                    "name":                 name,
                    "isin":                 isin,
                    "share_class":          "",
                    "folder":               entry.path.replace("\\", "/"),
                    "factsheet":            pdf.replace("\\", "/"),
                    "has_performance_data": os.path.isfile(os.path.join(entry.path, "performance_data.json")),
                    "has_portfolio_data":   os.path.isfile(os.path.join(entry.path, "fund_data.json")),
                    "updated":              today_str,
                })
        elif entry.is_file() and entry.name.endswith(".pdf") and not entry.name.startswith("."):
            stem = os.path.splitext(entry.name)[0]
            name = re.sub(r"[-_](factsheet|fact-sheet|en-gb|en-us).*$", "", stem, flags=re.I)
            name = re.sub(r"[-_]+", " ", name).title()
            funds.append({
                "name":                 name,
                "isin":                 "",
                "share_class":          "",
                "folder":               FACTSHEETS_DIR,
                "factsheet":            os.path.join(FACTSHEETS_DIR, entry.name).replace("\\", "/"),
                "has_performance_data": False,
                "has_portfolio_data":   False,
                "updated":              today_str,
            })

    return funds


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(FACTSHEETS_DIR, exist_ok=True)

    print("=" * 62)
    print("  Jupiter Asset Management — Fund Scraper (Playwright)")
    print("=" * 62)

    stats = {"processed": 0, "downloaded": 0, "errors": []}
    all_funds = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 900},
            accept_downloads=True,
            ignore_https_errors=True,
        )
        page = context.new_page()
        page.set_default_timeout(PAGE_TIMEOUT)

        # ── Step 1: get fund list ─────────────────────────────────────────────
        print("\n[1/3] Scraping fund list…")
        try:
            fund_list = get_fund_list(page)
        except Exception as e:
            print(f"  ✗ Fund list scraping failed: {e}")
            fund_list = []

        if not fund_list:
            print("\n  ℹ  No fund URLs found via scraping.")
            print("     The Jupiter website may have changed its structure,")
            print("     or JavaScript rendering took longer than expected.")
            print("\n     Falling back to existing PDFs in ./factsheets/ …")
            fallback = build_from_existing()
            if fallback:
                print(f"  Found {len(fallback)} existing PDF(s) — writing funds.json.")
            else:
                print("  No existing PDFs found either.")
                print(f"  → Manually download factsheets from jupiteram.com")
                print(f"  → Place them in ./{FACTSHEETS_DIR}/ and re-run this script.")
            with open(FUNDS_JSON, "w", encoding="utf-8") as f:
                json.dump(fallback, f, indent=2, ensure_ascii=False)
            print(f"\n  ✓ funds.json written ({len(fallback)} fund(s))")
            browser.close()
            print("\nDone.\n")
            return

        # ── Step 2: visit each fund page ──────────────────────────────────────
        print(f"\n[2/3] Processing {len(fund_list)} fund(s)…")
        for i, fund_info in enumerate(fund_list, 1):
            print(f"\n  [{i}/{len(fund_list)}]", end=" ")
            try:
                entry = process_fund(page, context, fund_info, stats)
                if entry:
                    all_funds.append(entry)
            except Exception as e:
                msg = f"{fund_info['name']}: unexpected error — {e}"
                print(f"     ✗ {msg}")
                stats["errors"].append(msg)

        browser.close()

    # ── Step 3: write funds.json ──────────────────────────────────────────────
    print(f"\n[3/3] Writing funds.json…")

    # Merge with any manually placed PDFs not found by the scraper
    scraped_isins = {f["isin"] for f in all_funds if f["isin"]}
    scraped_paths = {f["factsheet"] for f in all_funds if f["factsheet"]}
    for extra in build_from_existing():
        if extra["isin"] and extra["isin"] in scraped_isins:
            continue
        if extra["factsheet"] and extra["factsheet"] in scraped_paths:
            continue
        all_funds.append(extra)
        print(f"  ℹ  Added manually-placed PDF: {extra['name']}")

    with open(FUNDS_JSON, "w", encoding="utf-8") as f:
        json.dump(all_funds, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 62)
    print(f"  Complete.")
    print(f"  Funds processed : {stats['processed']}")
    print(f"  PDFs downloaded : {stats['downloaded']}")
    print(f"  Errors          : {len(stats['errors'])}")
    if stats["errors"]:
        print("\n  Error log:")
        for err in stats["errors"]:
            print(f"    • {err}")
    print(f"\n  funds.json — {len(all_funds)} fund(s) available.")
    print("=" * 62 + "\n")


if __name__ == "__main__":
    main()
