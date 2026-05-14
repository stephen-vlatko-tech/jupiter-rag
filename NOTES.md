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
