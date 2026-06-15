#!/usr/bin/env python3
"""
Update citation counts in publications.yml from the OpenAlex API.

Patches the YAML file in-place preserving existing formatting — no pyyaml
dependency needed. Uses Python stdlib (urllib, re, json, time) only.

Triggers:
  - Monthly cron via GitHub Actions
  - Manually via workflow_dispatch
  - On push with ``[citations]`` in commit message

OpenAlex API: https://docs.openalex.org/api-entities/works
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

PUBLICATIONS_PATH = "publications/publications.yml"
OPENALEX_API = "https://api.openalex.org/works"
USER_AGENT = "robinlovelace.net-citation-updater/1.0 (mailto:robinlovelace@users.noreply.github.com)"


# ── YAML line-level parser ─────────────────────────────────────────


def parse_entries(lines: list[str]) -> list[dict]:
    """Parse list-of-dict YAML, returning [(line_start, lines, doi), ...]."""
    entries = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("- key:"):
            start = i
            end = start + 1
            while end < len(lines) and not lines[end].startswith("- key:"):
                end += 1
            # Trim trailing blank lines from entry
            while end > start and lines[end - 1].strip() == "":
                end -= 1
            entry_lines = lines[start:end]
            doi = None
            for line in entry_lines:
                m = re.match(r"\s+doi:\s*(.*)", line)
                if m:
                    val = m.group(1).strip()
                    if val.startswith('"') and val.endswith('"'):
                        val = val[1:-1]
                    doi = val if val else None
            entries.append({
                "line_start": start,
                "lines": entry_lines,
                "doi": doi,
            })
            i = end
        else:
            i += 1
    return entries


def has_citations_block(lines: list[str]) -> bool:
    """Check if entry already has a ``citations:`` sub-field."""
    return any(line.strip().startswith("citations:") for line in lines)


# ── OpenAlex query ──────────────────────────────────────────────────


def query_batch(dois: list[str]) -> dict[str, int]:
    """Query OpenAlex for a batch of DOIs. Returns {doi: cited_by_count}."""
    doi_urls = [f"https://doi.org/{d}" for d in dois]
    filter_val = "doi:" + "|".join(doi_urls)
    params = urllib.parse.urlencode(
        {
            "filter": filter_val,
            "per_page": 100,
            "select": "doi,cited_by_count",
            "mailto": "robinlovelace@users.noreply.github.com",
        },
        safe="|",
    )
    url = f"{OPENALEX_API}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
    except Exception as exc:
        print(f"  [WARN] OpenAlex query failed: {exc}", file=sys.stderr)
        return {}

    results = {}
    for work in data.get("results", []):
        doi = work.get("doi", "")
        if doi:
            results[doi.replace("https://doi.org/", "")] = work.get(
                "cited_by_count", 0
            )
    return results


# ── YAML patcher ────────────────────────────────────────────────────


def patch_citations(lines: list[str], entries: list[dict],
                    citation_counts: dict[str, int]) -> int:
    """Patch ``lines`` (in-place) with citation data. Returns number of changes."""
    changes = 0
    today = time.strftime("%Y-%m-%d")

    # Track line offset caused by insertions so we don't lose our place
    offset_delta = 0

    for entry in entries:
        doi = entry["doi"]
        if not doi or doi not in citation_counts:
            continue

        count = citation_counts[doi]
        start = entry["line_start"] + offset_delta
        entry_lines = entry["lines"]

        if has_citations_block(entry_lines):
            # ── Update existing block ─────────────────────────
            # Scan the actual lines (accounting for previous insertions)
            for offset in range(len(entry_lines)):
                line = lines[start + offset]
                m = re.match(r"(\s+)openalex:\s*(\d+)", line)
                if m:
                    old = int(m.group(2))
                    if old == count:
                        break  # unchanged
                    lines[start + offset] = f"{m.group(1)}openalex: {count}\n"
                    # Update last_updated on the next line
                    if start + offset + 1 < len(lines):
                        lu_match = re.match(
                            r"(\s+)last_updated:\s*.*",
                            lines[start + offset + 1],
                        )
                        if lu_match:
                            lines[start + offset + 1] = (
                                f'{lu_match.group(1)}last_updated: "{today}"\n'
                            )
                    changes += 1
                    print(
                        f"  {doi:30s} {old:>5} → {count:>5}  "
                        f"({'▲' if count > old else '▼' if count < old else '—'})"
                    )
                    break
        else:
            # ── Insert new citations block ──────────────────
            insert_at = start + len(entry_lines)
            indent = "  "

            lines.insert(insert_at, f"{indent}citations:\n")
            lines.insert(insert_at + 1, f"{indent * 2}openalex: {count}\n")
            lines.insert(
                insert_at + 2, f'{indent * 2}last_updated: "{today}"\n'
            )
            lines.insert(insert_at + 3, "\n")
            offset_delta += 4
            changes += 1
            print(f"  {doi:30s} {'—':>5} → {count:>5}  (new)")

    return changes


# ── Main ────────────────────────────────────────────────────────────


def main():
    if not os.path.exists(PUBLICATIONS_PATH):
        print(f"File not found: {PUBLICATIONS_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(PUBLICATIONS_PATH, encoding="utf-8") as f:
        original_lines = f.readlines()

    entries = parse_entries(original_lines)
    dois = [(e["line_start"], e["doi"]) for e in entries if e.get("doi")]
    print(f"📄 {len(entries)} entries, {len(dois)} with DOIs")

    if not dois:
        sys.exit(0)

    all_dois = [d for _, d in dois]

    # Query in batches of 50 with a polite delay
    citation_counts: dict[str, int] = {}
    for i in range(0, len(all_dois), 50):
        batch = all_dois[i : i + 50]
        citation_counts.update(query_batch(batch))
        if i + 50 < len(all_dois):
            print(f"  ⌛ {min(i + 50, len(all_dois))}/{len(all_dois)} DOIs ...")
            time.sleep(0.1)

    print(f"📡 OpenAlex returned {len(citation_counts)}/{len(all_dois)} DOIs")

    changes = patch_citations(original_lines, entries, citation_counts)

    if changes:
        with open(PUBLICATIONS_PATH, "w", encoding="utf-8") as f:
            f.writelines(original_lines)  # modified in-place by patch_citations
        print(f"\n✅ {changes} citation count(s) updated in {PUBLICATIONS_PATH}")

        # Summary
        total = sum(
            citation_counts.get(e["doi"], 0) for e in entries if e.get("doi")
        )
        print(f"📊 Total OpenAlex citations: {total:,}")
    else:
        print("\n✅ Up to date — no changes needed")


if __name__ == "__main__":
    main()
