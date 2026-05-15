# Changelog

## Session 1 — 2026-05-13 — Initial build

- Built the full `jupiter-rag.html` application from scratch as a single self-contained HTML file
- Implemented RAG pipeline with PDF.js text extraction, TF-IDF chunk scoring, and Anthropic API integration
- Added API key gate with sessionStorage
- Added five team modes: Investment, Compliance, Marketing, Client Relations, Operations
- Added predictive question bar with fuzzy matching and per-team question banks
- Added document health check dashboard on PDF load
- Added confidence indicators, time saved estimates, and copy buttons on answers
- Added conversation memory panel showing chunks passed to Claude
- Added comparison mode for two documents simultaneously
- Added auto-generated briefing pack
- Added client letter drafting mode
- Dark navy and gold Jupiter aesthetic throughout
- Fixed CORS error by adding `anthropic-dangerous-direct-browser-access` header

---

## Session 2 — 2026-05-14 — Fund fetcher and initial selector

- Created `fetch_factsheets.py` to scrape jupiteram.com and download all available fund factsheet PDFs into a local `factsheets` folder
- Created `requirements.txt` with requests, beautifulsoup4, lxml
- Updated `run.bat` to run `fetch_factsheets.py` before starting the server
- Added fund selector above the existing upload zone in `jupiter-rag.html`, reading from `funds.json`
- Added "or" divider between fund selector and upload zone
- Selector hides automatically if `funds.json` is absent or empty
- No existing layout or functionality was changed

---

## Session 3 — 2026-05-14 — Attempted PDF preview panel (reverted)

- Attempted to add live PDF rendering to the left panel with gold citation highlights
- Feature broke the page layout and was reverted to the Session 2 state
- Revert commit pushed to GitHub at `f4cc8ba`

---

## Session 4 — 2026-05-14 — Documentation and housekeeping

- Updated `README.md` with full feature table, project structure tree, and accurate built-with section
- Updated `SETUP.md` with pip install step, fetch_factsheets step, and subsequent-runs section
- Added `.gitignore` excluding `factsheets/`, `funds.json`, Python cache, and OS files
- Added `CHANGELOG.md` and `NOTES.md`

---

## Session 6 — 2026-05-15 — Playwright scraper

- Replaced `fetch_factsheets.py` entirely with a Playwright headless browser scraper
- Scraper renders JavaScript pages so the full Jupiter fund list is discovered automatically
- Extracts structured per-fund data across four tabs: Overview, Performance, Portfolio, Documents
- Overview data: fund name, ISIN, share class, fund size, launch date, base currency, manager, benchmark, risk profile, domicile, legal structure, OCF, minimum investment, dealing frequency, cut-off time, ISA eligibility, investment objective
- Performance data: 1yr/3yr/5yr/10yr time series for fund and benchmark, discrete annual figures, cumulative figures
- Portfolio data: top 10 holdings with weights, geographic/sector/asset class breakdowns, total holdings count
- Documents: direct PDF download URLs for factsheet, KIID/KID, and prospectus
- Saves `fund_data.json` and `performance_data.json` per fund in per-ISIN subfolders inside `factsheets/`
- SHA-256 deduplication skips re-downloading unchanged PDFs
- Cookie and investor-type overlay dismissal handles Jupiter's consent gates automatically
- Fallback mode builds `funds.json` from any PDFs already present in `factsheets/` if scraping finds nothing
- `funds.json` entries now include `isin`, `share_class`, `folder`, `has_performance_data`, `has_portfolio_data`, and `updated` fields
- Added `playwright>=1.40.0` to `requirements.txt`
- Updated `run.bat` to silently run `pip install -r requirements.txt` and `playwright install chromium` before fetching
- Updated `SETUP.md` with Step 3a (`playwright install chromium`) and a note that first run may take several minutes

---

## Session 5 — 2026-05-14 — Fund search box

- Replaced the fund selector dropdown with a live search box styled to match the upload zone
- Search box has a dashed border, dark navy background, and gold accent on focus — visually consistent with the upload zone beneath it
- Shows all available funds on load; filters instantly as the user types
- Input clears and list resets after a fund is selected
- Upload zone label set to "Upload a Fund Document"
- Hidden automatically if `funds.json` is absent or empty; "or" divider hidden with it
- No other layout, panel, or functionality changed
