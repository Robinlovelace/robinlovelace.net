#!/usr/bin/env python3
"""
Generate publications.yml from my-citations-for-web.bib (canonical source).
Falls back to individual publication page frontmatter for entries not in the .bib.

Usage:
    python scripts/generate_publications_yml.py
    python scripts/generate_publications_yml.py --force   # always regenerate
"""

import os
import sys
import yaml
import re
import glob
from pathlib import Path

try:
    import bibtexparser
except ImportError:
    print("bibtexparser not installed. Install with: pip install bibtexparser")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIB_PATH = PROJECT_ROOT / "files" / "bibliography" / "my-citations-for-web.bib"
YML_PATH = PROJECT_ROOT / "publications" / "publications.yml"
PUBS_DIR = PROJECT_ROOT / "publications"

# Map of BibTeX entry types to publication types
TYPE_MAP = {
    "article": "Journal Article",
    "inproceedings": "Conference Paper",
    "incollection": "Book Chapter",
    "book": "Book",
    "phdthesis": "PhD Thesis",
    "mastersthesis": "Master's Thesis",
    "techreport": "Report",
    "misc": "Miscellaneous",
}

# Fields to copy directly from bib to yaml (with same name)
DIRECT_FIELDS = ["doi", "url", "year", "abstract"]

# Known individual page directories (to detect missing-from-bib entries)
def get_existing_dirs():
    dirs = set()
    for entry in PUBS_DIR.iterdir():
        if entry.is_dir() and (entry / "index.qmd").exists() and entry.name != "QA-PUBLICATIONS-2024-12-08":
            dirs.add(entry.name)
    return dirs

def slug_to_key(slug):
    """Convert a path slug to a YAML key."""
    return slug.replace("-", "_")

def parse_bib_entry(entry):
    """Convert a bibtexparser entry dict to a YAML publication entry."""
    eid = entry.get("ID", "")
    slug = eid.replace("_", "-")

    key = eid  # Use bibtex key directly
    title = entry.get("title", "").replace("{", "").replace("}", "")
    year = int(entry.get("year", 0)) if entry.get("year") else 0
    bib_type = entry.get("ENTRYTYPE", "misc").lower()
    
    # Clean author string
    author_raw = entry.get("author", "")
    authors = "; ".join(a for a in re.split(r"\s+and\s+", author_raw) if a) if author_raw else ""
    if authors:
        # Convert "Last, First and Last2, First2" to "First Last, First2 Last2"
        formatted_authors = []
        for a in re.split(r"\s+and\s+", author_raw):
            parts = [p.strip() for p in a.split(",")]
            if len(parts) >= 2:
                formatted_authors.append(f"{parts[1]} {parts[0]}")
            else:
                formatted_authors.append(parts[0])
        authors = ", ".join(formatted_authors)

    # Build entry
    entry_yml = {
        "key": key,
        "path": f"/publications/{slug}/",
        "title": title,
        "date": entry.get("year", f"{year}-01-01"),
        "year": year,
        "type": TYPE_MAP.get(bib_type, "Journal Article"),
        "venue": entry.get("journal", entry.get("booktitle", entry.get("publisher", ""))),
        "doi": entry.get("doi", ""),
        "url": entry.get("url", ""),
        "authors": authors,
        "abstract": entry.get("abstract", ""),
    }
    return entry_yml, slug


def parse_individual_page(slug):
    """Extract frontmatter from an individual publication page."""
    qmd_path = PUBS_DIR / slug / "index.qmd"
    if not qmd_path.exists():
        return None
    
    content = qmd_path.read_text()
    m = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not m:
        return None
    
    fm = yaml.safe_load(m.group(1))
    if not fm:
        return None
    
    title = fm.get("title", "")
    date_str = str(fm.get("date", ""))
    year = int(date_str[:4]) if date_str and len(date_str) >= 4 else 0
    venue = fm.get("venue", "")
    doi = fm.get("doi", "")
    pub_url = fm.get("publication-url", fm.get("url", ""))
    ctype = fm.get("citation-type-label", "")
    authors_list = fm.get("authors", [])
    authors_str = ", ".join(authors_list) if authors_list else ""
    abstract = fm.get("abstract", fm.get("description", ""))
    
    return {
        "key": slug_to_key(slug),
        "path": f"/publications/{slug}/",
        "title": title,
        "date": date_str,
        "year": year,
        "type": ctype or "Journal Article",
        "venue": venue,
        "doi": doi,
        "url": pub_url,
        "authors": authors_str,
        "abstract": abstract,
    }


def main():
    force = "--force" in sys.argv
    
    # Check if regeneration is needed
    if not force and YML_PATH.exists():
        bib_mtime = os.path.getmtime(BIB_PATH)
        yml_mtime = os.path.getmtime(YML_PATH)
        if yml_mtime > bib_mtime:
            print("publications.yml is newer than .bib file. Skipping (use --force to override).")
            return
    
    # Load BibTeX
    if not BIB_PATH.exists():
        print(f"Bib file not found: {BIB_PATH}")
        sys.exit(1)
    
    with open(BIB_PATH) as f:
        bib = bibtexparser.loads(f.read())
    
    # Map existing directory slugs (normalized for comparison)
    existing_dirs = get_existing_dirs()
    existing_dirs_norm = {re.sub(r'[-_]', '', d): d for d in existing_dirs}
    
    # Track which bib entries map to existing directories
    entries = []
    
    # Process each bib entry
    for entry in bib.entries:
        entry_yml, slug = parse_bib_entry(entry)
        entries.append(entry_yml)
    
    # Find individual page directories not in bib (normalized comparison)
    bib_slugs_norm = set()
    for e in bib.entries:
        s = e.get("ID", "").replace("_", "-")
        bib_slugs_norm.add(re.sub(r'[-_]', '', s))

    missing_slugs_norm = set(existing_dirs_norm.keys()) - bib_slugs_norm
    missing_slugs = {existing_dirs_norm[k] for k in missing_slugs_norm}
    if missing_slugs:
        print(f"Found {len(missing_slugs)} publication directories not in .bib (merging from page frontmatter):")
        for slug in sorted(missing_slugs):
            fm_entry = parse_individual_page(slug)
            if fm_entry:
                entries.append(fm_entry)
                print(f"  {slug}: {fm_entry['title'][:60]}")
            else:
                print(f"  {slug}: (could not parse frontmatter)")
    
    # Sort by year descending, then title
    entries.sort(key=lambda e: (-e["year"], e["title"]))
    
    # Write YAML
    with open(YML_PATH, "w") as f:
        yaml.dump(entries, f, default_flow_style=False, allow_unicode=True, width=120, sort_keys=False)
    
    print(f"\nGenerated publications.yml with {len(entries)} entries ({len(bib.entries)} from .bib + {len(missing_slugs)} from page frontmatter)")


if __name__ == "__main__":
    main()
