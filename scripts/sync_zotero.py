#!/usr/bin/env python3
"""
Sync publications bibliography from Zotero to ``my-citations-for-web.bib``.

Environment variables (set as GitHub Actions secrets):
  ZOTERO_API_KEY   — Zotero API key (Settings → Security → API keys)
  ZOTERO_USER_ID   — Numeric Zotero user ID (shown on the API keys page)

The fetched BibTeX file is saved to ``files/bibliography/my-citations-for-web.bib``.
On the next Quarto render, the existing pre-render hook
``scripts/generate_publications_yml.py`` regenerates ``publications.yml``.

Uses Python stdlib only (urllib).
"""

import os
import sys
import urllib.error
import urllib.request

BIB_PATH = "files/bibliography/my-citations-for-web.bib"
USER_AGENT = "robinlovelace.net-zotero-sync/1.0 (mailto:robinlovelace@users.noreply.github.com)"


def main():
    api_key = os.environ.get("ZOTERO_API_KEY")
    user_id = os.environ.get("ZOTERO_USER_ID")

    if not api_key:
        print("❌ ZOTERO_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    if not user_id:
        print("❌ ZOTERO_USER_ID environment variable not set", file=sys.stderr)
        sys.exit(1)

    # Fetch top-level items in BibTeX format (limit 100, generous for ~60 entries)
    url = f"https://api.zotero.org/users/{user_id}/items/top"
    params = "?format=bibtex&limit=100&itemType=-attachment%20%7C%7C%20-note"

    req = urllib.request.Request(
        url + params,
        headers={
            "Zotero-API-Key": api_key,
            "User-Agent": USER_AGENT,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            bibtex = resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 304:
            print("ℹ️  No changes since last fetch (304)")
            sys.exit(0)
        print(f"❌ HTTP {e.code}: {e.reason}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Failed to fetch from Zotero: {e}", file=sys.stderr)
        sys.exit(1)

    if not bibtex.strip():
        print("❌ Empty response from Zotero API", file=sys.stderr)
        sys.exit(1)

    # Check if content actually changed
    if os.path.exists(BIB_PATH):
        with open(BIB_PATH, encoding="utf-8") as f:
            old = f.read()
        if old == bibtex:
            print("✅ BibTeX content unchanged — up to date")
            sys.exit(0)

    # Write
    os.makedirs(os.path.dirname(BIB_PATH), exist_ok=True)
    with open(BIB_PATH, "w", encoding="utf-8") as f:
        f.write(bibtex)

    entry_count = bibtex.count("\n@")
    print(f"✅ Synced {BIB_PATH} from Zotero")
    print(f"   {len(bibtex):,} bytes · ~{entry_count} entries")

    # Output a summary for the workflow to use
    print(f"\nentries={entry_count}", flush=True)


if __name__ == "__main__":
    main()
