# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal portfolio and academic publications website for Joao Ferreira, hosted on GitHub Pages. Pure static site (HTML/CSS/JS) with one stdlib-only Python build script. No build system or static site generator.

**Live site:** `jpsferreira.github.io`

## Development

### Local Development
No build step required. Open `index.html` or `publications.html` directly in a browser, or use any local HTTP server:
```bash
python -m http.server 8000
```

### Python Scripts
Python 3.11+, **stdlib only — no dependencies, no venv needed**.

| Script | Purpose | Usage |
|--------|---------|-------|
| `build_publications.py` | Build `publications.json` + `stats.json` from the curated BibTeX + OpenAlex citation counts | `python3 build_publications.py` |
| `convert_gif_to_webm.py` | Batch convert GIFs to WebM (VP9, FFmpeg required) | `python convert_gif_to_webm.py images/` |

### Deployment
- **Automatic**: Push to `main` triggers GitHub Pages deploy via `.github/workflows/static.yml` (publishes the repo root verbatim — never commit secrets or `.venv/`)
- **Citations**: Refreshed weekly (Mon 6:00 UTC) via `.github/workflows/update-publications.yml`, which re-runs `build_publications.py`. GitHub disables the cron after ~60 days without repo activity — re-enable with `gh workflow enable update-publications.yml` if the bot commits stop.

## Architecture

### Pages
- **`index.html`** - Portfolio page with hero, project cards grid, about section, social links. All content is hardcoded HTML.
- **`publications.html`** - Publications page that dynamically loads data from JSON files via `assets/js/publications.js`.

### Data Pipeline
The publication list is **curated in the jpsferreira/cv repo** (`data/mypubs.bib` + `data/pub_categories.yaml`) and mirrored here in `publications_bib/`. To sync after CV changes:
```bash
cp ~/cv/data/mypubs.bib ~/cv/data/pub_categories.yaml publications_bib/
python3 build_publications.py
```
`build_publications.py` parses the bib, groups entries by category with the same stable descending IDs as the CV (A92…A1, PAT8…PAT1, …), enriches with OpenAlex per-DOI citation counts + author stats (h-index etc.), and writes `publications_bib/publications.json` + `publications_bib/stats.json`, which `publications.js` renders client-side (search/filter/sort, patents included).

### Styling
- Single stylesheet: `assets/css/modern.css` with CSS custom properties
- Dark theme: base `#0f172a`, accent `#38bdf8`
- Font: Inter (Google Fonts CDN)
- Icons: FontAwesome 6.4.0 + Academicons 1.9.4

### Key JavaScript
- `assets/js/publications.js` - Renders publications from JSON, handles filtering (type incl. patents, highly-cited), search, sorting (year/citations), stats display
- `assets/js/main.js` - Portfolio page interactions (scroll, navigation)

## Important Notes
- Bio numbers in `index.html` (papers/patents counts) are hardcoded — keep them consistent with `stats.json` when syncing
- Media in `images/` includes both source GIFs and optimized WebM videos
