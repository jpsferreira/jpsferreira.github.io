#!/usr/bin/env python3
"""
Fetch publications from Google Scholar and generate publications.json

Usage:
    pip install scholarly
    python fetch_scholar.py

This replaces the old BibTeX-based pipeline (convert_bib_to_json.py + mypubs.bib).
Publications are fetched directly from the Google Scholar profile.

Can be run locally or via the GitHub Action (.github/workflows/update-publications.yml).
"""

import json
import re
import time
from pathlib import Path

from scholarly import scholarly


SCHOLAR_USER_ID = "4evUtFkAAAAJ"
OUTPUT_FILE = Path("publications_bib/publications.json")


def fetch_author_publications():
    """Fetch all publications from Google Scholar author profile."""
    print(f"Fetching author profile: {SCHOLAR_USER_ID}")
    author = scholarly.search_author_id(SCHOLAR_USER_ID)
    author = scholarly.fill(author, sections=["basics", "indices", "publications"])

    print(f"Found {len(author['publications'])} publications")
    print(f"Citations: {author.get('citedby', 'N/A')}")
    print(f"h-index: {author.get('hindex', 'N/A')}")
    print(f"i10-index: {author.get('i10index', 'N/A')}")

    publications = []
    for i, pub in enumerate(author["publications"]):
        print(f"  [{i+1}/{len(author['publications'])}] Fetching: {pub['bib'].get('title', 'Unknown')[:60]}...")
        try:
            filled = scholarly.fill(pub)
        except Exception as e:
            print(f"    Warning: Could not fill details - {e}")
            filled = pub

        entry = convert_to_entry(filled)
        if entry:
            publications.append(entry)

        # Be polite to Google Scholar
        time.sleep(1)

    return publications, {
        "total_citations": author.get("citedby", 0),
        "h_index": author.get("hindex", 0),
        "i10_index": author.get("i10index", 0),
    }


def convert_to_entry(pub):
    """Convert a scholarly publication object to our JSON format."""
    bib = pub.get("bib", {})

    title = bib.get("title", "")
    if not title:
        return None

    # Determine publication type
    pub_type = "article"
    venue = bib.get("journal", "") or bib.get("conference", "") or ""
    if bib.get("pub_type"):
        pt = bib["pub_type"].lower()
        if "conference" in pt:
            pub_type = "inproceedings"
        elif "thesis" in pt:
            pub_type = "phdthesis" if "phd" in title.lower() else "mastersthesis"
        elif "book" in pt:
            pub_type = "book"

    # Extract year
    year = bib.get("pub_year", "")

    # Build author string
    authors = bib.get("author", "")
    if isinstance(authors, list):
        authors = " and ".join(authors)

    # Get citation count
    num_citations = pub.get("num_citations", 0)

    # Get URLs
    pub_url = pub.get("pub_url", "")
    eprint_url = pub.get("eprint_url", "")

    entry = {
        "type": pub_type,
        "key": pub.get("author_pub_id", title[:30].replace(" ", "_").lower()),
        "title": title,
        "author": authors,
        "year": str(year) if year else "",
        "citations": num_citations,
    }

    if venue:
        if pub_type == "inproceedings":
            entry["booktitle"] = venue
        else:
            entry["journal"] = venue

    if pub_url:
        entry["url"] = pub_url

    if eprint_url and eprint_url != pub_url:
        entry["eprint_url"] = eprint_url

    # Extract volume, number, pages if available
    if bib.get("volume"):
        entry["volume"] = str(bib["volume"])
    if bib.get("number"):
        entry["number"] = str(bib["number"])
    if bib.get("pages"):
        entry["pages"] = str(bib["pages"])

    return entry


def main():
    publications, stats = fetch_author_publications()

    # Sort by year (most recent first), then by citations
    def sort_key(entry):
        year = 0
        if entry.get("year"):
            match = re.search(r"(\d{4})", entry["year"])
            year = int(match.group(1)) if match else 0
        return (year, entry.get("citations", 0))

    publications.sort(key=sort_key, reverse=True)

    # Write publications JSON
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    print(f"\nWriting {len(publications)} entries to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(publications, f, indent=2, ensure_ascii=False)

    # Write stats JSON (for the frontend stats boxes)
    stats_file = OUTPUT_FILE.parent / "scholar_stats.json"
    stats["total_publications"] = len(publications)
    stats["articles"] = sum(1 for p in publications if p["type"] == "article")
    stats["last_updated"] = time.strftime("%Y-%m-%d")

    with open(stats_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)

    print(f"Writing stats to {stats_file}")
    print(f"\nDone! {len(publications)} publications fetched from Google Scholar.")
    print(f"  Articles: {stats['articles']}")
    print(f"  Total citations: {stats['total_citations']}")
    print(f"  h-index: {stats['h_index']}")
    print(f"  i10-index: {stats['i10_index']}")


if __name__ == "__main__":
    main()
