# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal portfolio and academic publications website for Joao Ferreira, hosted on GitHub Pages. Pure static site (HTML/CSS/JS) with Python automation scripts for data fetching. No build system or static site generator.

**Live site:** `jpsferreira.github.io`

## Development

### Local Development
No build step required. Open `index.html` or `publications.html` directly in a browser, or use any local HTTP server:
```bash
python -m http.server 8000
```

### Python Scripts
Requires Python 3.11+ with a virtual environment:
```bash
source .venv/bin/activate
pip install scholarly free-proxy
```

| Script | Purpose | Usage |
|--------|---------|-------|
| `fetch_scholar.py` | Fetch publications from Google Scholar (author ID: `4evUtFkAAAAJ`) | `python fetch_scholar.py` |
| `bootstrap_from_bib.py` | One-time BibTeX-to-JSON migration (historical) | `python bootstrap_from_bib.py` |
| `convert_gif_to_webm.py` | Batch convert GIFs to WebM (VP9, FFmpeg required) | `python convert_gif_to_webm.py images/` |

### Deployment
- **Automatic**: Push to `main` triggers GitHub Pages deploy via `.github/workflows/static.yml`
- **Publications**: Updated weekly (Mon 6:00 UTC) via `.github/workflows/update-publications.yml`, which runs `fetch_scholar.py` using `SCRAPER_API_KEY` secret for proxy

## Architecture

### Pages
- **`index.html`** - Portfolio page with hero, project cards grid, about section, social links. All content is hardcoded HTML.
- **`publications.html`** - Publications page that dynamically loads data from JSON files via `assets/js/publications.js`.

### Data Pipeline
`fetch_scholar.py` scrapes Google Scholar -> writes `publications_bib/publications.json` + `publications_bib/scholar_stats.json` -> `publications.js` reads these at runtime for client-side rendering with search/filter/sort.

### Styling
- Single stylesheet: `assets/css/modern.css` with CSS custom properties
- Dark theme: base `#0f172a`, accent `#38bdf8`
- Font: Inter (Google Fonts CDN)
- Icons: FontAwesome 6.4.0 + Academicons 1.9.4

### Key JavaScript
- `assets/js/publications.js` - Renders publications from JSON, handles filtering (type, year), search, sorting (year/citations), citation stats display
- `assets/js/main.js` - Portfolio page interactions (scroll, navigation)

## Important Notes
- No `requirements.txt` exists; Python deps are `scholarly` and `free-proxy`
- Scholar fetching uses ScraperAPI proxy in CI; falls back to free proxies locally
- `.venv/` is local only (gitignored)
- Media in `images/` includes both source GIFs and optimized WebM videos
