#!/usr/bin/env python3
"""Synchronise an explicitly curated Zotero collection as BibTeX.

The Zotero API limits multi-item requests to 100 results and an ``itemKey``
request to 50 keys. This script avoids a silent library-size cap by first
retrieving the complete key list (``format=keys`` has no maximum), then
exporting explicit 50-key batches as BibTeX. It follows Zotero pagination
links and refuses to replace the local bibliography if a batch is incomplete
or a DOI that already exists would gain a different citation key.

Set ``ZOTERO_API_KEY`` and ``ZOTERO_COLLECTION_KEY``. ``ZOTERO_USER_ID`` is
optional; when absent the script discovers the API key's user ID from
``/keys/current``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
from typing import Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen

API_ROOT = "https://api.zotero.org"
API_VERSION = "3"
BATCH_SIZE = 50  # Zotero documents itemKey lists as a maximum of 50 keys.
DEFAULT_BIB_PATH = Path("files/bibliography/my-citations-for-web.bib")
USER_AGENT = "robinlovelace.net-zotero-sync/2.0 (mailto:robinlovelace@users.noreply.github.com)"
ENTRY_HEADER = re.compile(r"(?m)^\s*@([A-Za-z]+)\s*[\{(]\s*([^,\s]+)\s*,")
DOI_FIELD = re.compile(r"(?im)^\s*doi\s*=\s*[\{\"]?([^\},\"\s]+)")


class ZoteroSyncError(RuntimeError):
    """A failed Zotero request or validation that must not overwrite source."""


def _request_with_headers(
    url: str, api_key: str, opener: Callable = urlopen
) -> tuple[str, dict[str, str]]:
    request = Request(
        url,
        headers={
            "Zotero-API-Key": api_key,
            "Zotero-API-Version": API_VERSION,
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with opener(request, timeout=30) as response:
            return response.read().decode("utf-8"), dict(response.headers)
    except Exception as exc:  # urllib errors provide useful status/reason text.
        raise ZoteroSyncError(f"Zotero request failed for {url}: {exc}") from exc


def _request(url: str, api_key: str, opener: Callable = urlopen) -> str:
    return _request_with_headers(url, api_key, opener)[0]


def next_page(link_header: str | None) -> str | None:
    """Extract Zotero's ``rel=next`` URL from an RFC 8288 Link header."""
    if not link_header:
        return None
    match = re.search(r'<([^>]+)>;\s*rel="?next"?', link_header)
    return match.group(1) if match else None


def discover_user_id(api_key: str, opener: Callable = urlopen) -> str:
    """Return the user ID tied to ``api_key`` without storing a second secret."""
    import json

    response = _request(f"{API_ROOT}/keys/current", api_key, opener)
    try:
        user_id = json.loads(response)["userID"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ZoteroSyncError("Zotero /keys/current returned no userID") from exc
    return str(user_id)


def publication_path(user_id: str, collection_key: str) -> str:
    """Return a deliberately curated collection endpoint, never full library."""
    return f"/users/{user_id}/collections/{collection_key}/items/top"


def fetch_item_keys(
    user_id: str,
    api_key: str,
    collection_key: str,
    opener: Callable = urlopen,
) -> list[str]:
    """Fetch every key in the explicitly selected publication collection."""
    params = urlencode({"format": "keys"})
    response = _request(
        f"{API_ROOT}{publication_path(user_id, collection_key)}?{params}", api_key, opener
    )
    keys = [key.strip() for key in response.splitlines() if key.strip()]
    if not keys:
        raise ZoteroSyncError("Zotero returned no top-level bibliography keys")
    if len(keys) != len(set(keys)):
        raise ZoteroSyncError("Zotero returned duplicate item keys")
    return keys


def count_bibtex_entries(text: str) -> int:
    """Count actual BibTeX entry headers, excluding ``@`` in field text."""
    return len(ENTRY_HEADER.findall(text))


def fetch_bibtex(
    user_id: str,
    api_key: str,
    collection_key: str,
    opener: Callable = urlopen,
) -> tuple[str, int]:
    """Export all selected keys in documented 50-key batches and validate them."""
    keys = fetch_item_keys(user_id, api_key, collection_key, opener)
    exports: list[str] = []
    for start in range(0, len(keys), BATCH_SIZE):
        batch = keys[start : start + BATCH_SIZE]
        params = urlencode(
            {
                "format": "bibtex",
                "limit": str(len(batch)),
                "itemKey": ",".join(batch),
            }
        )
        page_url = f"{API_ROOT}/users/{user_id}/items?{params}"
        pages: list[str] = []
        seen_urls: set[str] = set()
        while page_url:
            if page_url in seen_urls:
                raise ZoteroSyncError("Zotero pagination loop detected")
            seen_urls.add(page_url)
            page, headers = _request_with_headers(page_url, api_key, opener)
            pages.append(page.rstrip())
            page_url = next_page(headers.get("Link"))
        bibtex = "\n\n".join(pages) + "\n"
        count = count_bibtex_entries(bibtex)
        if count != len(batch):
            raise ValueError(
                f"Incomplete BibTeX export for keys {start + 1}-{start + len(batch)}: "
                f"expected {len(batch)} entries, received {count}"
            )
        exports.append(bibtex.rstrip() + "\n")
    combined = "\n".join(exports)
    total = count_bibtex_entries(combined)
    if total != len(keys):
        raise ValueError(
            f"Incomplete complete BibTeX export: expected {len(keys)} entries, received {total}"
        )
    return combined, total


def _doi_to_key(bibtex: str) -> dict[str, str]:
    """Map normalised DOI to citation key for the simple BibTeX used here."""
    matches = list(ENTRY_HEADER.finditer(bibtex))
    result: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(bibtex)
        doi_match = DOI_FIELD.search(bibtex[match.end() : end])
        if not doi_match:
            continue
        doi = doi_match.group(1).lower().removeprefix("https://doi.org/")
        if doi in result and result[doi] != match.group(2):
            raise ValueError(f"Duplicate DOI {doi} has multiple citation keys")
        result[doi] = match.group(2)
    return result


def validate_stable_keys(current: str, incoming: str) -> None:
    """Protect existing site entries from silent key changes or removals."""
    current_keys = _doi_to_key(current)
    incoming_keys = _doi_to_key(incoming)
    for doi, existing_key in current_keys.items():
        incoming_key = incoming_keys.get(doi)
        if incoming_key and incoming_key != existing_key:
            raise ValueError(
                f"citation key changed for DOI {doi}: {existing_key} -> {incoming_key}"
            )
    current_entry_keys = {key for _, key in ENTRY_HEADER.findall(current)}
    incoming_entry_keys = {key for _, key in ENTRY_HEADER.findall(incoming)}
    missing_keys = sorted(current_entry_keys - incoming_entry_keys)
    if missing_keys:
        preview = ", ".join(missing_keys[:5])
        suffix = "" if len(missing_keys) <= 5 else f" (+{len(missing_keys) - 5} more)"
        raise ValueError(f"incoming Zotero export is missing existing citation key(s): {preview}{suffix}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_BIB_PATH)
    parser.add_argument("--user-id", default=os.environ.get("ZOTERO_USER_ID"))
    parser.add_argument(
        "--collection-key",
        default=os.environ.get("ZOTERO_COLLECTION_KEY"),
        help="Zotero collection key containing the publications intended for this website",
    )
    parser.add_argument(
        "--api-key-env", default="ZOTERO_API_KEY", help="Environment variable holding the API key"
    )
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing output")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        print(f"{args.api_key_env} environment variable is not set", file=sys.stderr)
        return 2
    if not args.collection_key:
        print("ZOTERO_COLLECTION_KEY or --collection-key is required", file=sys.stderr)
        return 2
    try:
        user_id = args.user_id or discover_user_id(api_key)
        bibtex, count = fetch_bibtex(
            user_id=user_id, api_key=api_key, collection_key=args.collection_key
        )
        current = args.output.read_text(encoding="utf-8") if args.output.exists() else ""
        validate_stable_keys(current, bibtex)
    except (OSError, ValueError, ZoteroSyncError) as exc:
        print(f"Sync aborted: {exc}", file=sys.stderr)
        return 1

    if bibtex == current:
        print(f"Zotero bibliography already current ({count} entries).")
        return 0
    print(f"Validated {count} Zotero BibTeX entries.")
    if args.dry_run:
        print("Dry run: output was not written.")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(bibtex, encoding="utf-8")
    print(f"Updated {args.output}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
