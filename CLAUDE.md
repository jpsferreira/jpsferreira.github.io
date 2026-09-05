# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal site and publication list for João Ferreira, hosted on GitHub Pages. Pure static site (two HTML pages, one CSS file, one JS file) with one stdlib-only Python build script. No build system or static site generator.

**Live site:** `jpsferreira.github.io`

## Development

### Local Development
No build step required. Serve the repo root:
```bash
python3 -m http.server 8000
```
(`publications.html` fetches JSON, so open it through a server, not `file://`.)

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
- **`index.html`** — bio, experience, selected work, education, awards. All content is hardcoded HTML; the facts come from the CV repo (`~/cv/content/*.yaml`) and must be kept consistent with it.
- **`publications.html`** — reference list rendered from JSON by `assets/js/publications.js` (search, type filter, sort; default view is journal articles + patents; `?filter=patent` deep-links to the patents).
- **`cv.pdf`** — copy of `~/cv/build/jobs.pdf`; refresh it whenever the CV is re-rendered.

### Syncing from the CV repo
The publication list is **curated in the jpsferreira/cv repo** (`data/mypubs.bib` + `data/pub_categories.yaml`) and mirrored here in `publications_bib/`. After CV changes:
```bash
cp ~/cv/data/mypubs.bib ~/cv/data/pub_categories.yaml publications_bib/
cp ~/cv/build/jobs.pdf cv.pdf
python3 build_publications.py
```
`build_publications.py` parses the bib, groups entries by category with the same stable descending IDs as the CV (A92…A1, PAT8…PAT1, …), strips conference poster codes from display titles, enriches with OpenAlex per-DOI citation counts and author stats from Google Scholar (h-index, citations, i10; falls back to OpenAlex if Scholar blocks), and writes `publications_bib/publications.json` + `publications_bib/stats.json`.

### Styling
- Single stylesheet `assets/css/modern.css`, shared by both pages. Light editorial layout: off-white background, near-black text, one accent `#20586b` (same as the CV template). No icon fonts, no gradients, no cards.
- Font: Inter 400/600 (Google Fonts CDN) with system fallback.

## Important Notes
- Numbers in the `index.html` bio (journal papers, outputs, h-index, patents) are hardcoded — keep them consistent with `publications_bib/stats.json` and the CV's `content/02_executive_summary.yaml` when syncing.
- `images/me.jpg` is a small real photo (160×200) used as a placeholder; replace with a real headshot of at least 400×500 px when available. Never use AI-generated portraits.
- `images/` holds only the WebM demos referenced from `index.html`; keep GIF sources out of the repo (convert with `convert_gif_to_webm.py`).
