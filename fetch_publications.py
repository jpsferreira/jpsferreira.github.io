#!/usr/bin/env python3
"""
Fetch publications from OpenAlex API and generate publications.json

Usage:
    python fetch_publications.py

Uses the OpenAlex API (https://openalex.org) to fetch publications by ORCID.
No external dependencies required — uses only Python stdlib.

Can be run locally or via the GitHub Action (.github/workflows/update-publications.yml).
"""

import json
import re
import sys
import time
import urllib.request
import urllib.parse
from pathlib import Path


ORCID = "0000-0003-4310-2915"
OPENALEX_AUTHOR_ID = "A5001239416"
MAILTO = "jpsferreira@protonmail.com"
OUTPUT_FILE = Path("publications_bib/publications.json")
STATS_FILE = Path("publications_bib/scholar_stats.json")

BASE_URL = "https://api.openalex.org"

# OpenAlex type → BibTeX-style type used by publications.js
TYPE_MAP = {
    "article": "article",
    "journal-article": "article",
    "proceedings-article": "inproceedings",
    "book-chapter": "incollection",
    "book": "book",
    "dissertation": "phdthesis",
    "thesis": "phdthesis",
    "posted-content": "article",  # preprints
    "review": "article",
}


def api_get(path, params=None):
    """Make a GET request to the OpenAlex API and return parsed JSON."""
    if params is None:
        params = {}
    params["mailto"] = MAILTO
    url = f"{BASE_URL}{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fetch_author_stats():
    """Fetch author-level statistics from OpenAlex."""
    print(f"Fetching author stats: {OPENALEX_AUTHOR_ID}")
    author = api_get(f"/authors/{OPENALEX_AUTHOR_ID}")
    summary = author.get("summary_stats", {})
    return {
        "total_citations": author.get("cited_by_count", 0),
        "h_index": summary.get("h_index", 0),
        "i10_index": summary.get("i10_index", 0),
    }


def fetch_all_works():
    """Fetch all works for the author using cursor pagination."""
    works = []
    params = {
        "filter": f"author.orcid:{ORCID}",
        "sort": "publication_year:desc",
        "per_page": "100",
        "cursor": "*",
    }

    while True:
        print(f"  Fetching page (cursor={params['cursor'][:20]}...), {len(works)} so far")
        data = api_get("/works", params)
        results = data.get("results", [])
        if not results:
            break
        works.extend(results)
        next_cursor = data.get("meta", {}).get("next_cursor")
        if not next_cursor:
            break
        params["cursor"] = next_cursor

    print(f"Fetched {len(works)} works from OpenAlex")
    return works


def extract_authors(work):
    """Extract author string in 'Last, First and Last, First' format."""
    authorships = work.get("authorships", [])
    names = []
    for a in authorships:
        raw = a.get("raw_author_name") or a.get("author", {}).get("display_name", "")
        if raw:
            names.append(raw)
    return " and ".join(names)


def generate_key(work):
    """Generate a BibTeX-style key from first author surname and year."""
    authorships = work.get("authorships", [])
    surname = "unknown"
    if authorships:
        name = authorships[0].get("author", {}).get("display_name", "")
        if name:
            # Take last word as surname (handles "First Last" format)
            parts = name.strip().split()
            surname = parts[-1] if parts else "unknown"
            # Clean non-alphanumeric
            surname = re.sub(r"[^a-zA-Z]", "", surname)
    year = work.get("publication_year", "")
    return f"{surname}{year}"


def map_type(work):
    """Map OpenAlex work type to BibTeX-style type."""
    raw_type = (work.get("type") or "article").lower()
    return TYPE_MAP.get(raw_type, "article")


def convert_work(work):
    """Convert an OpenAlex work object to our JSON format."""
    title = work.get("display_name") or work.get("title", "")
    if not title:
        return None

    pub_type = map_type(work)
    year = work.get("publication_year")

    # Venue from primary_location
    venue = ""
    primary_loc = work.get("primary_location") or {}
    source = primary_loc.get("source") or {}
    venue = source.get("display_name", "")

    # URLs
    doi = work.get("doi", "")
    url = doi or primary_loc.get("landing_page_url", "")
    best_oa = work.get("best_oa_location") or {}
    pdf_url = best_oa.get("pdf_url", "")

    # Biblio details
    biblio = work.get("biblio") or {}
    volume = biblio.get("volume", "")
    issue = biblio.get("issue", "")
    first_page = biblio.get("first_page", "")
    last_page = biblio.get("last_page", "")
    pages = ""
    if first_page:
        pages = f"{first_page}-{last_page}" if last_page and last_page != first_page else first_page

    entry = {
        "type": pub_type,
        "key": generate_key(work),
        "title": title,
        "author": extract_authors(work),
        "year": str(year) if year else "",
        "citations": work.get("cited_by_count", 0),
    }

    if venue:
        if pub_type == "inproceedings":
            entry["booktitle"] = venue
        else:
            entry["journal"] = venue

    if url:
        entry["url"] = url
    if pdf_url and pdf_url != url:
        entry["eprint_url"] = pdf_url
    if volume:
        entry["volume"] = str(volume)
    if issue:
        entry["number"] = str(issue)
    if pages:
        entry["pages"] = pages

    return entry


def main():
    try:
        stats = fetch_author_stats()
    except Exception as e:
        print(f"Error fetching author stats: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"  Citations: {stats['total_citations']}, h-index: {stats['h_index']}, i10-index: {stats['i10_index']}")

    try:
        works = fetch_all_works()
    except Exception as e:
        print(f"Error fetching works: {e}", file=sys.stderr)
        sys.exit(1)

    publications = []
    for w in works:
        entry = convert_work(w)
        if entry:
            publications.append(entry)

    if not publications:
        print("Error: No publications fetched. Aborting to preserve existing data.", file=sys.stderr)
        sys.exit(1)

    # Deduplicate by key (keep first occurrence, which is most recent due to sort)
    seen_keys = set()
    unique = []
    for pub in publications:
        if pub["key"] not in seen_keys:
            seen_keys.add(pub["key"])
            unique.append(pub)
        else:
            # Append a suffix to make key unique
            i = 2
            new_key = f"{pub['key']}-{i}"
            while new_key in seen_keys:
                i += 1
                new_key = f"{pub['key']}-{i}"
            pub["key"] = new_key
            seen_keys.add(new_key)
            unique.append(pub)
    publications = unique

    # Sort by year desc, then citations desc
    def sort_key(entry):
        year = int(entry["year"]) if entry.get("year") and entry["year"].isdigit() else 0
        return (year, entry.get("citations", 0))

    publications.sort(key=sort_key, reverse=True)

    # Write publications JSON
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(publications)} entries to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(publications, f, indent=2, ensure_ascii=False)

    # Write stats JSON
    stats["total_publications"] = len(publications)
    stats["articles"] = sum(1 for p in publications if p["type"] == "article")
    stats["last_updated"] = time.strftime("%Y-%m-%d")

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Writing stats to {STATS_FILE}")
    print(f"\nDone! {len(publications)} publications fetched from OpenAlex.")
    print(f"  Articles: {stats['articles']}")
    print(f"  Total citations: {stats['total_citations']}")
    print(f"  h-index: {stats['h_index']}")
    print(f"  i10-index: {stats['i10_index']}")


if __name__ == "__main__":
    main()
