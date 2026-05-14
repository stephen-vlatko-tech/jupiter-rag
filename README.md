# Jupiter RAG — Document Intelligence Tool

A RAG-powered document intelligence tool built for Jupiter Asset Management. Automatically fetches all Jupiter fund factsheets, allows staff to select any fund from a dropdown and interrogate it in plain English using Claude AI — with live PDF preview and gold highlighted citations directly on the document pages.

## How to run

1. Install dependencies: `pip install -r requirements.txt`
2. Double-click `run.bat`

`run.bat` fetches the latest factsheets, starts the local server, and opens the app automatically. That's it.

Or follow the manual steps in [SETUP.md](SETUP.md).

## Requirements

- Python 3
- pip
- An Anthropic API key from [console.anthropic.com](https://console.anthropic.com)

## Team modes

The tool has five team modes, each with a tailored system prompt and pre-built question bank:

| Team | Focus |
|------|-------|
| **Investment** | Holdings, performance, risk, positioning, benchmark comparison |
| **Compliance** | FCA obligations, UCITS compliance, risk disclosures, restrictions |
| **Marketing** | Selling points, plain-English summaries, investor communications |
| **Client Relations** | Investor-facing explanations, share classes, dealing terms |
| **Operations** | ISINs, deadlines, service providers, fees, settlement terms |

## Key features

| Feature | Description |
|---------|-------------|
| **Automated fund fetching** | `fetch_factsheets.py` scrapes jupiteram.com and downloads all public factsheet PDFs |
| **Fund selector dropdown** | Reads `funds.json` on load — select any fund instantly, no manual upload needed |
| **Live PDF rendering** | Full visual rendering of the PDF in the left panel using PDF.js |
| **Gold citation highlights** | When Claude answers, the cited pages are highlighted in gold directly on the rendered document |
| **Click-to-jump citations** | Click any source in the chat panel to jump to that exact page and pulse-highlight it |
| **Page navigation** | Prev/Next buttons and a jump-to-page input in the document panel |
| **Document health check** | 6-criteria analysis runs automatically on load (risks, regulatory, performance, manager, fees, objective) |
| **Confidence indicator** | High / Medium / Low badge on every answer based on retrieval relevance scores |
| **Predictive question bar** | Fuzzy autocomplete question search, tailored to the active team |
| **Two-document comparison mode** | Load two PDFs side by side — all answers draw from both simultaneously |
| **Collapsible RAG memory panel** | Shows exactly which document chunks were sent to Claude for each answer |
| **Briefing pack generator** | Compiles the full conversation into formatted text ready for email or Word |
| **Client letter drafting** | Generates a complete investor update letter (retail / institutional / wholesale tone) |
| **Estimated time saved** | Each answer shows a rough calculation of manual search time saved |

## Built with

- [Anthropic Claude API](https://anthropic.com) — `claude-sonnet-4-20250514`
- [PDF.js](https://mozilla.github.io/pdf.js/) — PDF rendering and text extraction
- [Python requests](https://requests.readthedocs.io) + [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — factsheet scraping and downloading
- Vanilla JavaScript — no frameworks, no build step
