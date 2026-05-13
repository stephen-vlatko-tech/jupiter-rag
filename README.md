# Jupiter RAG — Document Intelligence Tool

A RAG-powered document intelligence tool built for Jupiter Asset Management.

## What it does

Allows Jupiter staff to interrogate fund factsheets and investor documents in plain English using Claude AI. Upload any fund document and ask questions directly — every answer is grounded in the document text, with source citations and page references.

## How to run

Double-click `run.bat` to start the local server and open the app automatically in your browser.

Or follow the manual steps in [SETUP.md](SETUP.md).

## Requirements

- Python (any recent version)
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

## Features

- PDF upload with automatic text extraction and chunking
- TF-IDF relevance scoring — only the most relevant sections are sent to Claude
- Document health check dashboard on load
- Confidence indicator (High / Medium / Low) on every answer
- Source citations with page numbers
- Predictive question bar with fuzzy autocomplete
- Two-document comparison mode
- Collapsible RAG memory panel (shows exactly what was sent to Claude)
- Auto-generated briefing pack from the full conversation
- Client letter drafting mode (retail / institutional / wholesale)
- Estimated time saved per answer

## Built with

- [Anthropic Claude API](https://anthropic.com) — claude-sonnet-4-20250514
- [PDF.js](https://mozilla.github.io/pdf.js/) — PDF text extraction
- Vanilla JavaScript — no frameworks, no build step
