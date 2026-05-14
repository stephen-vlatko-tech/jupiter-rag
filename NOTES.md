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
