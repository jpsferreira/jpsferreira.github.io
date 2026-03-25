#!/usr/bin/env python3
"""One-time script: convert existing mypubs.bib to the new publications.json format.
Run this once to bootstrap the data before the first Google Scholar sync."""

import re
import json
from pathlib import Path


ACCENT_MAP = {
    "'": {"a": "á", "e": "é", "i": "í", "o": "ó", "u": "ú", "A": "Á", "E": "É", "I": "Í", "O": "Ó", "U": "Ú"},
    "~": {"a": "ã", "o": "õ", "n": "ñ", "A": "Ã", "O": "Õ", "N": "Ñ"},
    "^": {"a": "â", "e": "ê", "i": "î", "o": "ô", "u": "û", "A": "Â", "E": "Ê", "O": "Ô"},
    '"': {"a": "ä", "e": "ë", "o": "ö", "u": "ü", "A": "Ä", "O": "Ö", "U": "Ü"},
    "`": {"a": "à", "e": "è", "o": "ò", "A": "À", "E": "È"},
    "c": {"c": "ç", "C": "Ç"},
}


def _replace_accent(match):
    cmd = match.group(1)
    char = match.group(2)
    return ACCENT_MAP.get(cmd, {}).get(char, char)


def clean_latex(text):
    if not text:
        return ""
    # Remove \textbf
    text = re.sub(r"\\textbf\{([^}]*)\}", r"\1", text)
    text = re.sub(r"\{\\textbf\s+([^}]*)\}", r"\1", text)
    # Handle accents: \'{e}, \~{a}, \^{e}, \"{o}, \c{c}, \`{e}
    text = re.sub(r"\\(['\~\^\"`c])\{(\w)\}", _replace_accent, text)
    # Handle: {\"o}, {\~a} etc
    text = re.sub(r"\{\\(['\~\^\"`c])(\w)\}", _replace_accent, text)
    # Handle: \'e (without braces)
    text = re.sub(r"\\(['\~\^\"`c])(\w)", _replace_accent, text)
    # Handle \c followed by space: \c c -> ç
    text = re.sub(r"\\c\s+(\w)", lambda m: ACCENT_MAP["c"].get(m.group(1), m.group(1)), text)
    # Handle LaTeX dotless i: \i -> i (used in e.g. Patr\'\i cia -> Patrícia)
    text = text.replace("\\i", "i")
    # Remove remaining backslash-quote combos
    text = re.sub(r"\\['\~\^\"`]", "", text)
    # Remove remaining braces
    text = re.sub(r"\{([^{}]*)\}", r"\1", text)
    text = text.replace("---", "\u2014").replace("--", "\u2013")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_bib(content):
    entries = []
    # Split on @ entries
    raw_entries = re.split(r"\n(?=@)", content)

    for raw in raw_entries:
        raw = raw.strip()
        if not raw.startswith("@"):
            continue

        # Get type and key
        header = re.match(r"@(\w+)\{([^,]+),", raw)
        if not header:
            continue

        entry_type = header.group(1).lower()
        key = header.group(2).strip()

        # Parse fields - handle multi-line values in braces
        fields = {}
        # Find all field = {value} or field = "value" or field = number
        field_pattern = re.compile(
            r"(\w+)\s*=\s*\{((?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*)\}"
            r"|(\w+)\s*=\s*\"([^\"]*)\""
            r"|(\w+)\s*=\s*(\d+)",
            re.DOTALL,
        )
        for fm in field_pattern.finditer(raw):
            if fm.group(1):
                fname = fm.group(1).lower()
                fval = fm.group(2)
            elif fm.group(3):
                fname = fm.group(3).lower()
                fval = fm.group(4)
            else:
                fname = fm.group(5).lower()
                fval = fm.group(6)
            fields[fname] = clean_latex(fval)

        title = fields.get("title", "")
        if not title:
            continue

        entry = {
            "type": entry_type,
            "key": key,
            "title": title,
            "author": fields.get("author", ""),
            "year": "",
            "citations": 0,
        }

        # Extract year
        year_str = fields.get("year", "")
        ym = re.search(r"(\d{4})", year_str)
        if ym:
            entry["year"] = ym.group(1)

        if fields.get("journal"):
            entry["journal"] = fields["journal"]
        elif fields.get("booktitle"):
            entry["booktitle"] = fields["booktitle"]
        elif fields.get("school"):
            entry["journal"] = fields["school"]

        if fields.get("volume"):
            entry["volume"] = fields["volume"]
        if fields.get("number"):
            entry["number"] = fields["number"]
        if fields.get("pages"):
            entry["pages"] = fields["pages"]

        # URL
        if fields.get("doi"):
            doi = fields["doi"]
            entry["url"] = doi if doi.startswith("http") else f"https://doi.org/{doi}"
        elif fields.get("url"):
            entry["url"] = fields["url"]

        entries.append(entry)

    return entries


def main():
    bib_file = Path("publications_bib/mypubs.bib")
    with open(bib_file, "r", encoding="utf-8") as f:
        content = f.read()

    entries = parse_bib(content)
    entries.sort(key=lambda e: int(e["year"]) if e["year"] else 0, reverse=True)

    out = Path("publications_bib/publications.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)

    stats = {
        "total_publications": len(entries),
        "total_citations": 0,
        "h_index": 0,
        "i10_index": 0,
        "articles": sum(1 for e in entries if e["type"] == "article"),
        "last_updated": "Pending first Scholar sync",
    }
    with open(Path("publications_bib/scholar_stats.json"), "w") as f:
        json.dump(stats, f, indent=2)

    print(f"Converted {len(entries)} publications")
    print(f"  Articles: {stats['articles']}")


if __name__ == "__main__":
    main()
