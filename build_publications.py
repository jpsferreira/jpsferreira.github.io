#!/usr/bin/env python3
"""
Build publications.json from the curated BibTeX (synced from the jpsferreira/cv repo)
and enrich it with citation counts + author stats from OpenAlex.

    python3 build_publications.py

Sources:
  publications_bib/mypubs.bib          — curated list (copy of ~/cv/data/mypubs.bib)
  publications_bib/pub_categories.yaml — category -> ordered bib keys (copy from ~/cv)
Outputs:
  publications_bib/publications.json   — list rendered by assets/js/publications.js
  publications_bib/stats.json          — author stats (OpenAlex) + counts

Stdlib only (the categories file is parsed with a tiny reader — it's a flat
"name:" + "  - key" YAML subset). Runs locally or in the weekly GitHub Action.
"""

import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

OPENALEX_AUTHOR_ID = "A5001239416"
MAILTO = "jpsferreira@protonmail.com"
BIB_FILE = Path("publications_bib/mypubs.bib")
CATEGORIES_FILE = Path("publications_bib/pub_categories.yaml")
OUTPUT_FILE = Path("publications_bib/publications.json")
STATS_FILE = Path("publications_bib/stats.json")

# category title -> (entry ID prefix, publications.js type filter)
CATEGORIES = {
    "Theses": ("T", "phdthesis"),
    "Papers in International Journals": ("A", "article"),
    "Book Chapters": ("L", "incollection"),
    "Journal Papers Resulting from International Conferences": ("C", "article"),
    "Indexed Papers Related to Participation in International Conferences": ("I", "inproceedings"),
    "Papers Related to Participation in International Conferences": ("P", "inproceedings"),
    "Papers Related to Participation in National Conferences": ("N", "inproceedings"),
    "Patents": ("PAT", "patent"),
}


# --- BibTeX parsing (vendored from jpsferreira/cv cvbuilder/bib.py) ----------

_ENTRY_RE = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,")


def parse_bib(text):
    entries = {}
    for m in _ENTRY_RE.finditer(text):
        start = text.index("{", m.start())
        depth, i = 0, start
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[m.end():i]
        entries[m.group(2)] = {"__type__": m.group(1).lower(), **_parse_fields(body)}
    return entries


def _parse_fields(body):
    fields, i = {}, 0
    field_re = re.compile(r"(\w[\w-]*)\s*=\s*", re.S)
    while (m := field_re.search(body, i)):
        j = m.end()
        if body[j] == "{" or body[j] == '"':
            close, depth, k = ("}" if body[j] == "{" else '"'), 0, j
            while k < len(body):
                if body[j] == "{":
                    if body[k] == "{":
                        depth += 1
                    elif body[k] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                elif body[k] == close and k > j:
                    break
                k += 1
            value, i = body[j + 1:k], k + 1
        else:
            k = body.find(",", j)
            k = len(body) if k == -1 else k
            value, i = body[j:k], k
        fields[m.group(1).lower()] = _clean(value)
    return fields


_ACCENTS = {
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "c": "ć", "n": "ń", "s": "ś",
          "y": "ý", "z": "ź", "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú"},
    "~": {"a": "ã", "o": "õ", "n": "ñ", "A": "Ã", "O": "Õ", "N": "Ñ"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û", "A": "Â", "E": "Ê", "O": "Ô"},
    "`": {"a": "à", "e": "è", "o": "ò", "A": "À"},
    '"': {"a": "ä", "e": "ë", "o": "ö", "u": "ü"},
    "c": {"c": "ç", "C": "Ç"},
}
_MACROS = {"---": "—", "--": "–", r"\textpm": "±", r"\ldots": "…", r"\textquoteright": "'", r"\textendash": "–",
           r"\textcopyright": "©", r"\%": "%", r"\_": "_", r"\&": "&", r"\\": " "}


def _clean(s):
    s = re.sub(r"\\(textbf|textit|emph|url)\b\s*", "", s)
    s = re.sub(r"\\i\b", "i", s)
    s = re.sub(r"\\(['~^`\"c])\s*\{?([a-zA-Z])\}?",
               lambda m: _ACCENTS.get(m.group(1), {}).get(m.group(2), m.group(2)), s)
    for macro, repl in _MACROS.items():
        s = s.replace(macro, repl)
    s = s.replace("~", " ")
    s = re.sub(r"[{}]", "", s)
    return re.sub(r"\s+", " ", s).strip()


def parse_categories(text):
    """Flat YAML subset: 'Name:' lines followed by '  - key' items; # comments."""
    cats, current = {}, None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- "):
            cats[current].append(stripped[2:].strip())
        elif stripped.endswith(":"):
            current = stripped[:-1]
            cats[current] = []
    return cats


# --- OpenAlex enrichment ------------------------------------------------------

def api_get(url):
    req = urllib.request.Request(url, headers={"User-Agent": f"mailto:{MAILTO}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def fetch_citations(dois):
    """DOI (lowercase) -> cited_by_count, batched 50 per request."""
    cites = {}
    dois = sorted(dois)
    for i in range(0, len(dois), 50):
        batch = dois[i:i + 50]
        flt = "doi:" + "|".join(batch)
        url = (f"https://api.openalex.org/works?filter={urllib.parse.quote(flt)}"
               f"&per-page=50&select=doi,cited_by_count&mailto={MAILTO}")
        try:
            data = api_get(url)
        except Exception as e:
            print(f"warning: citation batch {i // 50} failed: {e}", file=sys.stderr)
            continue
        for w in data.get("results", []):
            doi = (w.get("doi") or "").replace("https://doi.org/", "").lower()
            if doi:
                cites[doi] = w.get("cited_by_count", 0)
        time.sleep(0.3)
    return cites


def fetch_author_stats():
    try:
        a = api_get(f"https://api.openalex.org/authors/{OPENALEX_AUTHOR_ID}?mailto={MAILTO}")
        s = a.get("summary_stats", {})
        return {"total_citations": a.get("cited_by_count", 0),
                "h_index": s.get("h_index", 0), "i10_index": s.get("i10_index", 0)}
    except Exception as e:
        print(f"warning: author stats failed: {e}", file=sys.stderr)
        return {}


# --- build --------------------------------------------------------------------

def main():
    bib = parse_bib(BIB_FILE.read_text())
    cats = parse_categories(CATEGORIES_FILE.read_text())

    dois = {f["doi"].lower().removeprefix("https://doi.org/")
            for f in bib.values() if f.get("doi")}
    print(f"bib: {len(bib)} entries, {len(dois)} with DOI; querying OpenAlex…")
    cites = fetch_citations(dois)
    author_stats = fetch_author_stats()

    pubs = []
    for cat, keys in cats.items():
        prefix, jstype = CATEGORIES.get(cat, ("", "article"))
        n = len(keys)
        for i, key in enumerate(keys):
            f = bib.get(key)
            if f is None:
                sys.exit(f"error: key {key!r} in pub_categories.yaml missing from bib")
            doi = (f.get("doi") or "").lower().removeprefix("https://doi.org/")
            year = re.search(r"\d{4}", f.get("year", "") or "")
            is_patent = f["__type__"] == "patent"
            entry = {
                "type": "patent" if is_patent else jstype,
                "key": key,
                "id": f"{prefix}{n - i}",
                "category": cat,
                "title": f.get("title", "Untitled"),
                "author": f.get("author", ""),
                "year": year.group() if year else "",
                "citations": cites.get(doi, 0),
                "journal": (f.get("number", "") + " · " + f.get("note", "")).strip(" ·")
                           if is_patent else
                           (f.get("journal") or f.get("booktitle") or f.get("publisher") or ""),
                "url": f"https://doi.org/{doi}" if doi else (f.get("url") or ""),
            }
            for opt in ("volume", "number", "pages"):
                if not is_patent and f.get(opt):
                    entry[opt] = f[opt]
            pubs.append(entry)

    if not pubs:
        sys.exit("error: zero publications built — refusing to overwrite existing data")

    pubs.sort(key=lambda p: (-int(p["year"] or 0), p["category"], p["id"]))

    stats = {
        **author_stats,
        "total_publications": len(pubs),
        "articles": sum(1 for p in pubs if p["type"] == "article"),
        "patents": sum(1 for p in pubs if p["type"] == "patent"),
        "source": "curated BibTeX (jpsferreira/cv) + OpenAlex citations",
        "last_updated": date.today().isoformat(),
    }

    OUTPUT_FILE.write_text(json.dumps(pubs, indent=1, ensure_ascii=False))
    STATS_FILE.write_text(json.dumps(stats, indent=1, ensure_ascii=False))
    matched = sum(1 for p in pubs if p["citations"])
    print(f"wrote {OUTPUT_FILE} ({len(pubs)} entries, {matched} with citation counts)")
    print(f"wrote {STATS_FILE}: {stats}")


if __name__ == "__main__":
    main()
