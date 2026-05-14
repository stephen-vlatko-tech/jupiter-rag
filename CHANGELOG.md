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

## Session 5 — 2026-05-14 — Fund search box

- Replaced the fund selector dropdown with a live search box styled to match the upload zone
- Search box has a dashed border, dark navy background, and gold accent on focus — visually consistent with the upload zone beneath it
- Shows all available funds on load; filters instantly as the user types
- Input clears and list resets after a fund is selected
- Upload zone label set to "Upload a Fund Document"
- Hidden automatically if `funds.json` is absent or empty; "or" divider hidden with it
- No other layout, panel, or functionality changed
