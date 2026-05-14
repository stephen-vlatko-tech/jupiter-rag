# Setup

**Requirements:** Python 3, pip, an Anthropic API key

---

## Steps

**Step 1:** Get an Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

**Step 2:** Open a terminal in `C:\projects\Jupiter-RAG`

**Step 3:** Install dependencies
```
pip install -r requirements.txt
```

**Step 4:** Download all Jupiter fund factsheets
```
python fetch_factsheets.py
```
This may take a few minutes on first run. On subsequent runs it skips files that haven't changed.

**Step 5:** Launch the app — either:
- Double-click `run.bat` to do everything automatically (fetches latest factsheets, starts server, opens browser), or
- Manually run `python -m http.server 8000` and open `http://localhost:8000/jupiter-rag.html`

**Step 6:** Enter your Anthropic API key when prompted on first load

**Step 7:** Select a fund from the dropdown or upload your own PDF

---

> **Note:** `run.bat` automatically fetches the latest factsheets every time it is run, so the fund list stays up to date.

> **Note:** Never open the HTML file directly from your file system — it must be served via the local server or the app will not work.
