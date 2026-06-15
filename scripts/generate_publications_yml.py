#!/usr/bin/env python3
"""
Generate publications.yml from my-citations-for-web.bib (canonical source).
Falls back to individual publication page frontmatter for entries not in .bib.

No external dependencies — uses Python stdlib only.
"""

import os
import sys
import re
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIB_PATH = PROJECT_ROOT / "files" / "bibliography" / "my-citations-for-web.bib"
YML_PATH = PROJECT_ROOT / "publications" / "publications.yml"
PUBS_DIR = PROJECT_ROOT / "publications"

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


# ── Minimal BibTeX parser (stdlib only) ──────────────────────────

def parse_bibtex(text):
    """Parse BibTeX text. Returns list of dicts with keys: type, id, fields."""
    entries = []
    # Match @type{key,  ...  }
    pattern = re.compile(
        r"@(\w+)\s*\{\s*([^,]+)\s*,"  # @type{key,
        r"((?:.|\n)*?)\}\s*",         # content...
        re.MULTILINE
    )
    for m in pattern.finditer(text):
        entry_type = m.group(1).lower()
        entry_id = m.group(2).strip()
        body = m.group(3)
        fields = _parse_bib_fields(body)
        entries.append({"type": entry_type, "id": entry_id, "fields": fields})
    return entries


def _parse_bib_fields(body):
    """Parse bib field key = {value} pairs from body text."""
    fields = {}
    # Match:  key = {value}  or  key = "value"
    pattern = re.compile(
        r"(\w+)\s*=\s*"         # key =
        r"(\{)"                 # opening brace
        r"((?:.|\n)*?)"         # value (non-greedy)
        r"\}"                   # closing brace
        r"\s*,?\s*",
        re.MULTILINE
    )
    for m in pattern.finditer(body):
        key = m.group(1).lower()
        val = m.group(3).strip()
        # Unescape braces
        val = val.replace("\\{", "{").replace("\\}", "}")
        fields[key] = val
    return fields


def clean_bib_string(s):
    """Remove curly braces from a bibtex string value."""
    return s.replace("{", "").replace("}", "")


def format_authors(author_raw):
    """Convert 'Last, First and Last2, First2' to 'First Last, First2 Last2'."""
    if not author_raw:
        return ""
    authors = []
    for part in re.split(r"\s+and\s+", author_raw.strip()):
        part = part.strip()
        if "," in part:
            bits = [p.strip() for p in part.split(",", 1)]
            authors.append(f"{bits[1]} {bits[0]}")
        else:
            authors.append(part)
    return ", ".join(authors)


def bib_to_yml_entry(entry):
    """Convert a parsed bib entry dict to a YAML publication entry dict."""
    eid = entry["id"]
    slug = eid.strip("_-").replace("_", "-")
    fields = entry["fields"]

    title = clean_bib_string(fields.get("title", ""))
    year_str = fields.get("year", "0")
    year = int(year_str) if year_str.isdigit() else 0
    bib_type = entry["type"]

    authors = format_authors(fields.get("author", ""))

    venue = fields.get("journal",
                       fields.get("booktitle",
                                   fields.get("publisher",
                                               fields.get("school", ""))))
    doi = fields.get("doi", "")
    url = fields.get("url", "")
    abstract = fields.get("abstract", "")

    return {
        "key": eid,
        "path": f"/publications/{slug}/",
        "title": title,
        "date": f"{year:04d}-01-01" if year else "",
        "year": year,
        "type": TYPE_MAP.get(bib_type, "Journal Article"),
        "venue": venue,
        "doi": doi,
        "url": url,
        "authors": authors,
        "abstract": abstract,
        "_slug": slug,
    }


# ── Individual page frontmatter parser ──────────────────────────

def parse_frontmatter(text):
    """Simple YAML-like frontmatter parser. Returns dict or None."""
    m = re.match(r"^---\n(.*?)\n(?:---|\.\.\.)", text, re.DOTALL)
    if not m:
        return None
    raw = m.group(1)
    result = {}
    # Simple key: value parser (handles lists with - items)
    lines = raw.split("\n")
    current_key = None
    current_list = None
    for line in lines:
        list_match = re.match(r"^\s+-\s+(.+)$", line)
        kv_match = re.match(r"^(\w[\w-]*)\s*:\s*(.*)$", line)
        if kv_match:
            current_key = kv_match.group(1)
            val = kv_match.group(2).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            elif val.startswith("'") and val.endswith("'"):
                val = val[1:-1]
            # Check if value is a list (actually starts with [)
            if val == "" or val == "[]":
                result[current_key] = val
                current_list = None
            elif val.startswith("["):
                # Inline list
                result[current_key] = val
                current_list = None
            else:
                result[current_key] = val
                current_list = None
        elif list_match and current_key:
            if current_key not in result or not isinstance(result.get(current_key), list):
                result[current_key] = []
            val = list_match.group(1).strip()
            if val.startswith('"') and val.endswith('"'):
                val = val[1:-1]
            result[current_key].append(val)
    return result


def parse_individual_page(slug):
    """Extract frontmatter from an individual publication page. Returns dict or None."""
    qmd_path = PUBS_DIR / slug / "index.qmd"
    if not qmd_path.exists():
        return None

    content = qmd_path.read_text(encoding="utf-8")
    fm = parse_frontmatter(content)
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
    if isinstance(authors_list, str):
        authors_list = [a.strip() for a in authors_list.split(",") if a.strip()]
    authors_str = ", ".join(authors_list) if isinstance(authors_list, list) else authors_list
    abstract = fm.get("abstract", fm.get("description", ""))

    return {
        "key": slug.replace("-", "_"),
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


# ── Manual YAML writer (stdlib only) ────────────────────────────

def yaml_value(val, indent=0):
    """Format a single YAML value."""
    prefix = "  " * indent
    if val is None or val == "":
        return '""'
    if isinstance(val, bool):
        return "true" if val else "false"
    if isinstance(val, int):
        return str(val)
    # String — quote if it contains special chars
    s = str(val)
    if any(ch in s for ch in (':', '#', '{', '}', '[', ']', ',', '&', '*', '?', '|', '-', '<', '>', '=', '!', '%', '@', '`')):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if s == "" or s.startswith(" ") or s.endswith(" "):
        escaped = s.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return s


def write_yaml(entries, path):
    """Write a list of dicts as YAML to path."""
    lines = []
    for entry in entries:
        lines.append("- key: " + yaml_value(entry.get("key", "")))
        for field in ["path", "title", "date", "year", "type", "venue", "doi", "url", "authors", "abstract"]:
            val = entry.get(field, "")
            # Skip empty abstract to keep file tidy
            if field == "abstract" and not val:
                continue
            if field == "year":
                lines.append(f"  {field}: {yaml_value(val, 2)}")
            else:
                # Check if value needs quoting
                formatted = yaml_value(val)
                if formatted.startswith('"') or formatted == "true" or formatted == "false":
                    lines.append(f"  {field}: {formatted}")
                else:
                    lines.append(f"  {field}: {formatted}")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Main ────────────────────────────────────────────────────────

def get_existing_dirs():
    """Get set of publication directory slugs."""
    dirs = set()
    for entry in PUBS_DIR.iterdir():
        if entry.is_dir() and (entry / "index.qmd").exists() and "QA-PUBLICATIONS" not in entry.name:
            dirs.add(entry.name)
    return dirs


def main():
    force = "--force" in sys.argv

    # Check if regeneration is needed
    if not force and YML_PATH.exists():
        bib_mtime = os.path.getmtime(BIB_PATH)
        yml_mtime = os.path.getmtime(YML_PATH)
        if yml_mtime > bib_mtime:
            print("publications.yml is newer than .bib file. Skipping (use --force to override).")
            return

    # Load and parse BibTeX
    if not BIB_PATH.exists():
        print(f"Bib file not found: {BIB_PATH}")
        sys.exit(1)

    bib_text = BIB_PATH.read_text(encoding="utf-8")
    bib_entries = parse_bibtex(bib_text)

    # Build normalized lookup
    existing_dirs = get_existing_dirs()
    existing_dirs_norm = {re.sub(r'[-_]', "", d): d for d in existing_dirs}

    # Convert bib entries
    entries = []
    bib_slugs_norm = set()
    for entry in bib_entries:
        yml_entry = bib_to_yml_entry(entry)
        entries.append(yml_entry)
        bib_slugs_norm.add(re.sub(r'[-_]', "", yml_entry["_slug"]))

    # Merge entries from individual pages not in bib
    missing_norm = set(existing_dirs_norm.keys()) - bib_slugs_norm
    missing_slugs = {existing_dirs_norm[k] for k in missing_norm}
    if missing_slugs:
        print(f"Found {len(missing_slugs)} publication directories not in .bib (merging):")
        for slug in sorted(missing_slugs):
            fm = parse_individual_page(slug)
            if fm:
                entries.append(fm)
                print(f"  {slug}: {fm['title'][:60]}")
            else:
                print(f"  {slug}: (could not parse frontmatter)")

    # Sort: year desc, then title asc
    entries.sort(key=lambda e: (-e["year"], e["title"]))

    # Write YAML
    write_yaml(entries, YML_PATH)

    print(f"\nGenerated publications.yml with {len(entries)} entries "
          f"({len(bib_entries)} from .bib + {len(missing_slugs)} from page frontmatter)")


if __name__ == "__main__":
    main()
