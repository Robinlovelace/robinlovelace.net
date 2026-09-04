#!/usr/bin/env python3
"""Discover recent publications from OpenAlex, verified by Crossref.

Zotero remains canonical. This job only maintains provisional records for works
that are absent from the Zotero BibTeX source; the publication generator
suppresses a provisional record as soon as a matching Zotero DOI exists.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "publication-discovery.json"
CANONICAL_BIB = ROOT / "files" / "bibliography" / "my-citations-for-web.bib"
OUTPUT_PATH = ROOT / "publications" / "discovered-publications.json"
OPENALEX_API = "https://api.openalex.org"
CROSSREF_API = "https://api.crossref.org"
USER_AGENT = "robinlovelace.net-publication-discovery/1.0 (https://robinlovelace.net/)"


def normalize_doi(value: str) -> str:
    """Return a comparable DOI, accepting common resolver prefixes."""
    value = (value or "").strip().lower()
    value = re.sub(r"^doi:\s*", "", value)
    value = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", value)
    return value.rstrip(" .;,)")


def normalized_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (value or "").lower()).strip()


def title_similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalized_title(left), normalized_title(right)).ratio()


def get_json(url: str) -> dict:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=30) as response:  # nosec B310: fixed HTTPS APIs
        return json.loads(response.read().decode("utf-8"))


def crossref_record(doi: str) -> dict | None:
    try:
        return get_json(f"{CROSSREF_API}/works/{doi}").get("message")
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None


def fetch_openalex_works(config: dict) -> list[dict]:
    """Cursor-page all configured recent works for the stable author identifier."""
    cursor = "*"
    works = []
    filters = [
        f"author.id:{config['openalex_author_id']}",
        f"from_publication_date:{config['from_publication_date']}",
    ]
    while cursor:
        params = {
            "filter": ",".join(filters),
            "per-page": 200,
            "cursor": cursor,
            "select": "id,doi,display_name,publication_date,type,authorships,primary_location",
        }
        payload = get_json(f"{OPENALEX_API}/works?{urlencode(params)}")
        works.extend(payload.get("results", []))
        cursor = payload.get("meta", {}).get("next_cursor")
    return works


def authors_from_crossref(record: dict) -> str:
    people = []
    for person in record.get("author", []):
        name = " ".join(part for part in [person.get("given", ""), person.get("family", "")] if part)
        if name:
            people.append(name)
    return ", ".join(people)


def candidate_from_records(work: dict, crossref: dict) -> dict:
    doi = normalize_doi(work.get("doi", ""))
    title = (crossref.get("title") or [work.get("display_name", "")])[0]
    published = crossref.get("published-online") or crossref.get("published-print") or crossref.get("issued") or {}
    date_parts = published.get("date-parts", [[work.get("publication_date", "")[:4] or 0]])[0]
    year = int(date_parts[0]) if date_parts and str(date_parts[0]).isdigit() else int(work["publication_date"][:4])
    venue = (crossref.get("container-title") or [work.get("primary_location", {}).get("source", {}).get("display_name", "")])[0]
    return {
        "key": "openalex-" + work["id"].rstrip("/").split("/")[-1].lower(),
        "path": f"https://doi.org/{doi}",
        "title": title,
        "date": f"{year:04d}-01-01",
        "year": year,
        "type": "Journal Article",
        "venue": venue,
        "doi": doi,
        "url": crossref.get("URL", f"https://doi.org/{doi}"),
        "authors": authors_from_crossref(crossref),
        "abstract": "",
        "provenance": {
            "status": "provisional",
            "openalex_id": work["id"],
            "crossref": True,
            "detected_from": "OpenAlex author feed, verified against Crossref DOI metadata",
        },
    }


def select_candidates(
    works: list[dict],
    known_dois: set[str],
    known_titles: set[str],
    config: dict,
    fetch_crossref,
) -> list[dict]:
    """Select only new, configured, Crossref-title-verified DOI records."""
    excluded = [re.compile(pattern, re.IGNORECASE) for pattern in config.get("excluded_title_regex", [])]
    selected = []
    for work in works:
        doi = normalize_doi(work.get("doi", ""))
        title = work.get("display_name", "")
        if not doi or doi in known_dois or normalized_title(title) in known_titles:
            continue
        allowed_types = config.get("allowed_work_types", [])
        if allowed_types and work.get("type") not in allowed_types:
            continue
        if any(pattern.search(title) for pattern in excluded):
            continue
        crossref = fetch_crossref(doi)
        if not crossref or not crossref.get("title"):
            continue
        if title_similarity(title, crossref["title"][0]) < config.get("minimum_title_similarity", 0.9):
            continue
        selected.append(candidate_from_records(work, crossref))
    return sorted(selected, key=lambda item: (-item["year"], item["title"]))


def canonical_identities() -> tuple[set[str], set[str]]:
    text = CANONICAL_BIB.read_text(encoding="utf-8")
    doi_pattern = re.compile(r'(?im)^\s*doi\s*=\s*[{\"]?([^}\",\s]+)')
    title_pattern = re.compile(r'(?ims)^\s*title\s*=\s*[{\"](.+?)[}\"]\s*,')
    dois = {normalize_doi(value) for value in doi_pattern.findall(text)}
    titles = {normalized_title(value) for value in title_pattern.findall(text)}
    return dois - {""}, titles - {""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report candidates without writing JSON")
    args = parser.parse_args()
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    known_dois, known_titles = canonical_identities()
    candidates = select_candidates(fetch_openalex_works(config), known_dois, known_titles, config, crossref_record)
    payload = {"schema_version": 1, "source": "OpenAlex + Crossref", "records": candidates}
    print(f"Found {len(candidates)} provisional publication record(s).")
    for candidate in candidates:
        print(f"- {candidate['title']} ({candidate['doi']})")
    if not args.dry_run:
        OUTPUT_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Publication discovery failed without modifying sources: {exc}", file=sys.stderr)
        raise SystemExit(1)
