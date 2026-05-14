# Setup

**Requirements:** Python 3, pip, an Anthropic API key

---

## First-time setup

**Step 1:** Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

**Step 2:** Open a terminal in `C:\projects\Jupiter-RAG`

**Step 3:** Install Python dependencies
```
pip install -r requirements.txt
```

**Step 4:** Download Jupiter fund factsheets
```
python fetch_factsheets.py
```
This scrapes jupiteram.com and downloads all available fund factsheet PDFs into `./factsheets/`. It may take a few minutes on first run. On subsequent runs it skips files that haven't changed.

**Step 5:** Launch the app
```
Double-click run.bat
```
This runs `fetch_factsheets.py`, starts the local server on port 8000, and opens the app in your browser automatically.

Or start manually:
```
python -m http.server 8000
```
Then open `http://localhost:8000/jupiter-rag.html`.

**Step 6:** Enter your Anthropic API key when prompted on first load. It is stored in session memory only and never sent to Jupiter servers.

**Step 7:** Select a fund from the dropdown, or drag and drop your own PDF.

---

## Subsequent runs

Just double-click `run.bat`. It fetches the latest factsheets (skipping unchanged files), starts the server, and opens the browser.

---

## Notes

- `run.bat` automatically runs the factsheet fetcher every time, so the fund list stays up to date
- Never open the HTML file directly from the file system — it must be served via the local server or the app will not work (CORS restriction)
- The `factsheets/` folder and `funds.json` are local only and should not be committed to GitHub
- If `funds.json` is absent (e.g. after a fresh clone), the fund selector will not appear — run `fetch_factsheets.py` or drag and drop a PDF manually
