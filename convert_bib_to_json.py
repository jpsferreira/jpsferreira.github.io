#!/usr/bin/env python3
"""
Convert BibTeX file to JSON for web display
Run this script whenever you update your .bib file:
    python convert_bib_to_json.py
"""

import json
import re
from pathlib import Path
import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode


def remove_textbf(text):
    """Remove \textbf commands but keep the content"""
    if not text:
        return ''
    # Remove \textbf{...} keeping the content
    text = re.sub(r'\\textbf\{([^}]*)\}', r'<strong>\1</strong>', text)
    text = re.sub(r'\{\\textbf\s+([^}]*)\}', r'<strong>\1</strong>', text)
    return text


def clean_latex(text):
    """Remove LaTeX commands and convert to plain text"""
    if not text:
        return ''
    
    # Remove \textbf but convert to HTML strong tags
    text = remove_textbf(text)
    
    # Remove other LaTeX formatting
    text = re.sub(r'\\textit\{([^}]*)\}', r'<em>\1</em>', text)
    text = re.sub(r'\\text\{([^}]*)\}', r'\1', text)
    
    # Handle special punctuation
    text = text.replace('---', '—')
    text = text.replace('--', '–')
    text = text.replace('``', '"')
    text = text.replace("''", '"')
    
    # Remove remaining braces
    text = re.sub(r'\{([^{}]*)\}', r'\1', text)
    
    # Clean up whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def customizations(record):
    """Apply customizations to BibTeX entries"""
    # Convert to unicode (handles LaTeX accents automatically)
    record = convert_to_unicode(record)
    
    # Clean all fields
    for key, value in record.items():
        if isinstance(value, str):
            record[key] = clean_latex(value)
    
    return record


def parse_bibtex(bib_content):
    """Parse BibTeX content and return list of entries"""
    # Remove \textbf from the entire content, but handle nested braces carefully
    # Match \textbf{...} where ... can contain nested braces
    def replace_textbf(match):
        content = match.group(1)
        return '{<strong>' + content + '</strong>}'
    
    # This regex handles one level of nesting
    bib_content = re.sub(r'\\textbf\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', replace_textbf, bib_content)
    bib_content = re.sub(r'\{\\textbf\s+([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', replace_textbf, bib_content)
    
    # Parse with bibtexparser
    parser = BibTexParser(common_strings=True)
    parser.customization = customizations
    parser.ignore_nonstandard_types = False
    parser.homogenize_fields = False
    
    # Add common string definitions
    parser.bib_database.strings['en'] = 'en'
    parser.bib_database.strings['english'] = 'english'
    
    bib_database = bibtexparser.loads(bib_content, parser=parser)
    
    # Convert to list of dictionaries
    entries = []
    for entry in bib_database.entries:
        # Rename ENTRYTYPE to type and ID to key for consistency
        entry_dict = {
            'type': entry.get('ENTRYTYPE', '').lower(),
            'key': entry.get('ID', '')
        }
        # Add all other fields
        for key, value in entry.items():
            if key not in ['ENTRYTYPE', 'ID']:
                entry_dict[key.lower()] = value
        
        entries.append(entry_dict)
    
    return entries


def main():
    # Read BibTeX file
    bib_file = Path('publications_bib/mypubs.bib')
    
    if not bib_file.exists():
        print(f"Error: {bib_file} not found!")
        return
    
    print(f"Reading {bib_file}...")
    with open(bib_file, 'r', encoding='utf-8') as f:
        bib_content = f.read()
    
    # Parse BibTeX
    print("Parsing BibTeX entries...")
    entries = parse_bibtex(bib_content)
    
    # Sort by year (most recent first)
    def get_year(entry):
        if 'year' in entry:
            match = re.search(r'(\d{4})', entry['year'])
            return int(match.group(1)) if match else 0
        return 0
    
    entries.sort(key=get_year, reverse=True)
    
    # Write JSON file
    output_file = Path('publications_bib/publications.json')
    print(f"Writing {len(entries)} entries to {output_file}...")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, indent=2, ensure_ascii=False)
    
    print(f"✓ Successfully converted {len(entries)} publications!")
    print(f"  - Journal articles: {sum(1 for e in entries if e['type'] == 'article')}")
    print(f"  - Conference papers: {sum(1 for e in entries if e['type'] == 'inproceedings')}")
    print(f"  - Theses: {sum(1 for e in entries if e['type'] in ['phdthesis', 'mastersthesis'])}")


if __name__ == '__main__':
    main()
