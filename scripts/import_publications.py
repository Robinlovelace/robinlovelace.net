#!/usr/bin/env python3
"""Generate Quarto publication pages and listing data from a BibTeX file.

This script uses Pandoc's BibTeX reader to convert `.bib` input to CSL JSON,
then writes:

1. per-publication `index.qmd` pages under `publications/<slug>/`
2. matching `entry.bib` files for each publication
3. a `publications/publications.yml` data file for future listings/tables

The script is intentionally dependency-light so it can live inside this site
repo and be extracted into a standalone package later if it proves useful.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


TYPE_LABELS = {
    "article-journal": "Journal Article",
    "article-magazine": "Magazine Article",
    "article-newspaper": "Newspaper Article",
    "bill": "Bill",
    "book": "Book",
    "broadcast": "Broadcast",
    "chapter": "Book Chapter",
    "classic": "Classic",
    "collection": "Collection",
    "dataset": "Dataset",
    "document": "Document",
    "entry": "Entry",
    "entry-dictionary": "Dictionary Entry",
    "entry-encyclopedia": "Encyclopedia Entry",
    "event": "Event",
    "figure": "Figure",
    "graphic": "Graphic",
    "hearing": "Hearing",
    "interview": "Interview",
    "legal_case": "Legal Case",
    "legislation": "Legislation",
    "manuscript": "Manuscript",
    "map": "Map",
    "motion_picture": "Motion Picture",
    "paper-conference": "Conference Paper",
    "pamphlet": "Pamphlet",
    "patent": "Patent",
    "performance": "Performance",
    "personal_communication": "Personal Communication",
    "post": "Post",
    "post-weblog": "Blog Post",
    "regulation": "Regulation",
    "report": "Report",
    "review": "Review",
    "review-book": "Book Review",
    "software": "Software",
    "song": "Song",
    "speech": "Speech",
    "standard": "Standard",
    "thesis": "Thesis",
    "treaty": "Treaty",
    "webpage": "Web Page",
}


@dataclass
class Publication:
    key: str
    slug: str
    title: str
    authors: list[str]
    date: str
    year: int | None
    venue: str
    pub_type: str
    pub_type_label: str
    doi: str
    url: str
    abstract: str
    citation: str
    bibtex: str


def run_pandoc(bib_path: Path) -> list[dict[str, Any]]:
    result = subprocess.run(
        ["pandoc", "-f", "bibtex", "-t", "csljson", str(bib_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(result.stdout)


def split_bibtex_entries(text: str) -> dict[str, str]:
    entries: dict[str, str] = {}
    current: list[str] = []
    current_key: str | None = None
    depth = 0

    for line in text.splitlines():
        if current_key is None:
            match = re.match(r"@\w+\s*\{\s*([^,]+),", line)
            if match:
                current_key = match.group(1).strip()
                current = [line]
                depth = line.count("{") - line.count("}")
            continue

        current.append(line)
        depth += line.count("{") - line.count("}")
        if depth <= 0:
            entries[current_key] = "\n".join(current).strip() + "\n"
            current_key = None
            current = []
            depth = 0

    return entries


def strip_braces(value: str) -> str:
    value = value.replace("{", "").replace("}", "")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"stats19", "stats-19", value)
    value = re.sub(r"([0-9]{4})([a-z])$", r"\1-\2", value)
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-{2,}", "-", value).strip("-")
    return value or "publication"


def yaml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def date_from_parts(item: dict[str, Any]) -> tuple[str, int | None]:
    parts = item.get("issued", {}).get("date-parts", [])
    if not parts:
        return "", None
    first = parts[0]
    year = first[0] if len(first) > 0 else None
    month = first[1] if len(first) > 1 else 1
    day = first[2] if len(first) > 2 else 1
    if year is None:
        return "", None
    return f"{year:04d}-{month:02d}-{day:02d}", year


def person_name(person: dict[str, Any]) -> str:
    literal = person.get("literal")
    if literal:
        return strip_braces(literal)
    family = strip_braces(person.get("family", ""))
    given = strip_braces(person.get("given", ""))
    return " ".join(part for part in [given, family] if part).strip()


def authors_string(authors: list[str]) -> str:
    if not authors:
        return ""
    if len(authors) == 1:
        return authors[0]
    if len(authors) == 2:
        return f"{authors[0]} and {authors[1]}"
    return f"{', '.join(authors[:-1])}, and {authors[-1]}"


def venue_from_item(item: dict[str, Any]) -> str:
    for field in [
        "container-title",
        "publisher",
        "collection-title",
        "event-title",
    ]:
        value = item.get(field)
        if isinstance(value, list):
            value = value[0] if value else ""
        if value:
            return strip_braces(str(value))
    return ""


def make_citation(item: dict[str, Any], authors: list[str], year: int | None, venue: str) -> str:
    title = strip_braces(item.get("title", ""))
    author_part = authors_string(authors)
    pieces = []
    if author_part:
        pieces.append(author_part)
    if year is not None:
        pieces.append(f"({year}).")
    if title:
        pieces.append(f"{title}.")
    if venue:
        pieces.append(f"*{venue}*.")
    doi = strip_braces(item.get("DOI", ""))
    if doi:
        pieces.append(f"https://doi.org/{doi}")
    return " ".join(piece for piece in pieces if piece).strip()


def publication_from_item(item: dict[str, Any], bibtex: str) -> Publication:
    key = item["id"]
    slug = slugify(key.replace("_", "-"))
    authors = [person_name(person) for person in item.get("author", []) if person_name(person)]
    date, year = date_from_parts(item)
    venue = venue_from_item(item)
    pub_type = item.get("type", "document")
    pub_type_label = TYPE_LABELS.get(pub_type, pub_type.replace("-", " ").title())
    title = strip_braces(item.get("title", key))
    doi = strip_braces(item.get("DOI", ""))
    url = strip_braces(item.get("URL", ""))
    abstract = strip_braces(item.get("abstract", ""))
    citation = make_citation(item, authors, year, venue)
    return Publication(
        key=key,
        slug=slug,
        title=title,
        authors=authors,
        date=date,
        year=year,
        venue=venue,
        pub_type=pub_type,
        pub_type_label=pub_type_label,
        doi=doi,
        url=url,
        abstract=abstract,
        citation=citation,
        bibtex=bibtex,
    )


def qmd_body(publication: Publication) -> str:
    lines: list[str] = [
        "---",
        f"title: {yaml_quote(publication.title)}",
        f"description: {yaml_quote(publication.citation or publication.title)}",
        f"date: {yaml_quote(publication.date or '')}",
        "title-block-banner: false",
        "toc: false",
        f"citation-key: {yaml_quote(publication.key)}",
        f"citation-type: {yaml_quote(publication.pub_type)}",
        f"citation-type-label: {yaml_quote(publication.pub_type_label)}",
        f"venue: {yaml_quote(publication.venue)}",
        f"doi: {yaml_quote(publication.doi)}",
        f"publication-url: {yaml_quote(publication.url)}",
        "authors:",
    ]
    if publication.authors:
        lines.extend([f"  - {yaml_quote(author)}" for author in publication.authors])
    else:
        lines.append("  - \"\"")
    if publication.abstract:
        lines.append(f"abstract: {yaml_quote(publication.abstract)}")
    lines.extend(
        [
            "---",
            "",
            f"**Type:** {publication.pub_type_label}",
        ]
    )
    if publication.venue:
        lines.append(f"**Venue:** {publication.venue}")
    if publication.year is not None:
        lines.append(f"**Year:** {publication.year}")
    lines.append("")

    link_bits = []
    if publication.doi:
        link_bits.append(f"[DOI](https://doi.org/{publication.doi})")
    if publication.url:
        label = "Publisher Link" if publication.doi and publication.url.rstrip("/") != f"https://doi.org/{publication.doi}" else "URL"
        link_bits.append(f"[{label}]({publication.url})")
    link_bits.append("[BibTeX](entry.bib)")
    lines.append(" ".join(link_bits))
    lines.append("")

    if publication.abstract:
        lines.extend(
            [
                "## Abstract",
                "",
                publication.abstract,
                "",
            ]
        )

    lines.extend(
        [
            "## Citation",
            "",
            publication.citation or publication.title,
            "",
            "## BibTeX",
            "",
            "```bibtex",
            publication.bibtex.rstrip(),
            "```",
            "",
            "## Notes",
            "",
            "{{< include _notes.qmd >}}",
            "",
        ]
    )
    return "\n".join(lines)


def yaml_list_item(publication: Publication) -> str:
    lines = [
        f"- key: {yaml_quote(publication.key)}",
        f"  path: {yaml_quote(f'/publications/{publication.slug}/')}",
        f"  title: {yaml_quote(publication.title)}",
        f"  date: {yaml_quote(publication.date)}",
        f"  year: {publication.year if publication.year is not None else 'null'}",
        f"  type: {yaml_quote(publication.pub_type_label)}",
        f"  venue: {yaml_quote(publication.venue)}",
        f"  doi: {yaml_quote(publication.doi)}",
        f"  url: {yaml_quote(publication.url)}",
        f"  authors: {yaml_quote(', '.join(publication.authors))}",
        f"  abstract: {yaml_quote(publication.abstract)}",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bibtex", type=Path, help="Input BibTeX file")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "publications",
        help="Directory for generated publication pages",
    )
    parser.add_argument(
        "--copy-to",
        type=Path,
        default=ROOT / "files" / "bibliography" / "my-citations-for-web.bib",
        help="Copy the source BibTeX file to this path before generating pages",
    )
    args = parser.parse_args()

    source_bib = args.bibtex.resolve()
    output_dir = args.output_dir.resolve()
    copy_to = args.copy_to.resolve()

    copy_to.parent.mkdir(parents=True, exist_ok=True)
    if source_bib != copy_to:
        shutil.copy2(source_bib, copy_to)

    bib_text = copy_to.read_text(encoding="utf-8")
    bib_entries = split_bibtex_entries(bib_text)
    csl_items = run_pandoc(copy_to)

    output_dir.mkdir(parents=True, exist_ok=True)

    publications: list[Publication] = []
    for item in csl_items:
        key = item["id"]
        bibtex = bib_entries.get(key)
        if not bibtex:
            raise KeyError(f"Missing original BibTeX for key {key}")
        publication = publication_from_item(item, bibtex)
        publications.append(publication)

        pub_dir = output_dir / publication.slug
        pub_dir.mkdir(parents=True, exist_ok=True)
        (pub_dir / "index.qmd").write_text(qmd_body(publication), encoding="utf-8")
        (pub_dir / "entry.bib").write_text(publication.bibtex, encoding="utf-8")
        notes_path = pub_dir / "_notes.qmd"
        if not notes_path.exists():
            notes_path.write_text("", encoding="utf-8")

    publications.sort(key=lambda pub: (pub.year or 0, pub.title.lower()), reverse=True)
    data_text = "\n".join(yaml_list_item(publication) for publication in publications) + "\n"
    (output_dir / "publications.yml").write_text(data_text, encoding="utf-8")

    print(
        f"Imported {len(publications)} publications from {os.path.relpath(copy_to, ROOT)} "
        f"into {os.path.relpath(output_dir, ROOT)}"
    )


if __name__ == "__main__":
    main()
