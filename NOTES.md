# Notes

## Known issues

- `fetch_factsheets.py` may not find all funds depending on Jupiter website structure — may need manual URL updates if scraping breaks
- Live PDF preview with citation highlighting was attempted but broke the layout — needs a different approach next session
- The app must always be served via `python -m http.server 8000` and never opened directly from the file system due to CORS restrictions

---

## Ideas for future sessions

- Revisit the live PDF preview panel as a collapsible sidebar or modal overlay rather than replacing the existing left panel — this approach is less likely to break the layout
- Add metric comparison between two loaded fund factsheets — side by side scoring across key metrics like fees, performance, risk rating, geographic exposure
- Add a core summary of differences between two factsheets broken down by team type — compliance differences, investment differences, client relations differences etc
- Clean up and declutter the overall UI — it is currently too busy
- Consider adding a progress bar or status indicator when `fetch_factsheets.py` is running so the user knows it has not frozen

---

## Future Architecture — Production Build

The current app is a single HTML file that calls the Anthropic API directly from the browser. This works for local demos but is not suitable for a publicly hosted website where multiple users need to access it without their own API key.

The full production architecture requires two upgrades:

### Problem 1 — Scraping

`fetch_factsheets.py` currently uses requests and BeautifulSoup which cannot render JavaScript. Jupiter's website requires JavaScript to load the fund list so the scraper finds nothing. The fix is to upgrade to Playwright, a headless browser library that can render JavaScript pages and properly scrape all fund factsheet links automatically. This would make `run.bat` fully automated with no manual PDF downloads needed.

### Problem 2 — Public deployment

For a proper public website a small Flask backend is needed that:

- Holds the Anthropic API key securely server-side so visitors never need their own key
- Handles all Claude API calls server-side rather than from the browser
- Serves the fund factsheets and `funds.json` to the frontend
- The HTML frontend talks to the Flask backend instead of directly to the Anthropic API

**Hosting:** Railway or Render rather than Netlify since a running server is required.

### Planned sessions

- **Session A:** Build Flask backend with Playwright scraping and Anthropic API proxy
- **Session B:** Update frontend to talk to Flask backend instead of Anthropic directly
- **Session C:** Deploy to Railway or Render and test end to end

**Estimated cost:** 2–5 million tokens, roughly $8–20 in API costs.

### Short-term fix before 2026-05-18

Manually download 5–6 Jupiter fund factsheets from jupiteram.com and place them in the `factsheets` folder. Run `python fetch_factsheets.py` and it will generate `funds.json` from whatever PDFs are present. This gives the fund selector working functionality for the demo without needing the full production build.

---

## Production Build Roadmap

A full step-by-step plan for turning the current local demo into a production-ready publicly hosted application.

---

### Phase 1 — Playwright Scraper (1 session, est. 500k–1M tokens)

Replaces `fetch_factsheets.py` entirely with a headless browser scraper that can render JavaScript.

**What to build:**

- Install Playwright and Chromium via pip
- Script visits the Jupiter fund centre at `jupiteram.com/uk/en/individual/fund-centre/`, waits for JavaScript to fully render, extracts every fund name and individual fund page URL
- Visits each fund page one by one and extracts all structured data from the Overview, Performance, Portfolio, and Documents tabs
- From **Overview tab:** fund name, share class, ISIN, fund size, launch date, base currency, fund manager name, investment objective, risk and reward profile score, benchmark name, fund domicile, legal structure, ongoing charges figure, minimum investment amounts, dealing frequency, cut-off times, available share classes, ISA eligibility
- From **Performance tab:** time series data points for 1yr, 3yr, 5yr, 10yr for both the fund and benchmark, discrete annual performance figures, cumulative performance figures
- From **Portfolio tab:** top 10 holdings with percentage weights, geographic allocation breakdown, sector allocation breakdown, asset class breakdown, total number of holdings
- From **Documents tab:** direct PDF download URLs for factsheet, KIID or KID, and prospectus
- Downloads the factsheet PDF for each fund
- Saves `fund_data.json` and `performance_data.json` per fund inside a folder named by ISIN inside the `factsheets` directory
- Updates `funds.json` with the full fund list
- Updates `requirements.txt` with playwright added
- Updates `run.bat` to run the new scraper instead of the old `fetch_factsheets.py`

---

### Phase 2 — Flask Backend (1 session, est. 500k–1M tokens)

Moves the Anthropic API calls server-side so a public URL works without users needing their own API key.

**What to build:**

- A Flask app called `server.py`
- Endpoint that receives questions and document chunks from the frontend and calls the Anthropic API server-side using a stored API key
- Endpoint that serves `funds.json` and fund PDFs to the frontend
- Endpoint that serves `fund_data.json` and `performance_data.json` per fund
- Anthropic API key stored in a `.env` file that is never committed to GitHub
- Add `python-dotenv` and `flask` to `requirements.txt`
- Update `run.bat` to start Flask instead of `python -m http.server`
- Update `.gitignore` to exclude `.env` and the `factsheets` folder

---

### Phase 3 — Frontend Update to Use Flask Backend (1 session, est. 1–2M tokens)

Updates `jupiter-rag.html` to talk to Flask instead of the Anthropic API directly.

**What to change:**

- Replace all direct Anthropic API fetch calls with calls to the local Flask endpoints
- Remove the API key gate entirely since the key is now server-side
- Update the fund selector to load `funds.json` from the Flask server
- Update PDF loading to fetch PDFs from the Flask server
- Load `fund_data.json` alongside each PDF to enrich Claude context with structured data so answers about holdings, fees, performance, and geographic exposure draw from structured JSON rather than unreliable PDF text extraction
- Add a **Performance tab** alongside the existing team tabs containing an interactive Chart.js line chart
- The performance chart should: allow the user to select any loaded funds and overlay their performance lines on the same chart, show the benchmark line, support time period selection of 1yr, 3yr, 5yr, and 10yr, allow toggling individual fund lines on and off, show percentage return on Y axis and dates on X axis, and use the existing gold colour palette
- When comparison mode is active with two funds loaded, automatically show both funds overlaid on the performance chart
- Keep all existing functionality intact: team tabs, predictive question bar, document health check, comparison mode, briefing pack, client letter drafting

---

### Phase 4 — Document Viewer Panel (1 session, est. 1–2M tokens)

Adds a PDF preview panel as a collapsible sidebar on the right-hand side without touching existing panels.

**What to build:**

- A collapsible panel on the right side of the screen triggered by a Sources button in the top right corner — slides in from the right without replacing or moving any existing content
- Renders the full PDF visually using PDF.js showing actual document pages as they appear
- Smooth scrolling through all pages within the panel
- When Claude answers a question, cited passages are highlighted in gold directly on the rendered PDF pages
- The page containing the first citation automatically scrolls into view when an answer is given
- Clicking a source citation in the chat jumps the viewer to that exact page and pulses the highlight so it is easy to locate
- Page navigation controls at the bottom of the panel: previous page, next page, current page number indicator
- Panel can be closed and reopened without losing its state or scroll position
- On mobile the panel takes full screen when open

---

### Phase 5 — Deployment to Railway or Render (1 session, est. 300–500k tokens)

Takes the local Flask app and deploys it as a live public URL.

**What to build:**

- A `Procfile` telling Railway or Render how to start the Flask server
- Environment variable configuration for the Anthropic API key on the hosting platform so it is never exposed
- Update all frontend URLs to point to the production server rather than localhost
- Test the full flow end to end on the live URL
- Update `README.md` with the live URL and deployment instructions

---

### Total estimates

- 5 Claude Code sessions
- 3–6 million tokens total
- Roughly $15–30 in API costs
- Realistically 2–3 evenings of work

### Recommended order

Complete Phase 1 first as it is self-contained and fixes the fund selector for the demo. Complete Phases 2–5 after the dinner once there is a clearer picture of what the target audience wants to see.
