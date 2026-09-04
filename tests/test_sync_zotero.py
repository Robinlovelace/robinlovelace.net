from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse
import unittest


SCRIPT = Path(__file__).parents[1] / "scripts" / "sync_zotero.py"
spec = importlib.util.spec_from_file_location("sync_zotero", SCRIPT)
sync_zotero = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync_zotero)


class FakeResponse:
    def __init__(self, body: str, headers: dict[str, str] | None = None):
        self.body = body.encode("utf-8")
        self.headers = headers or {}

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class ZoteroExportTests(unittest.TestCase):
    def test_exports_all_keys_in_batches_without_a_fixed_library_limit(self):
        keys = [f"KEY{i:05d}" for i in range(101)]
        calls = []

        def opener(request, timeout=30):
            parsed = urlparse(request.full_url)
            query = parse_qs(parsed.query)
            calls.append(query)
            if query.get("format") == ["keys"]:
                return FakeResponse("\n".join(keys) + "\n")
            requested = query["itemKey"][0].split(",")
            body = "\n".join(
                f"@article{{key_{key},\n  doi = {{10.1/{key}}}\n}}" for key in requested
            )
            return FakeResponse(body)

        bibtex, exported = sync_zotero.fetch_bibtex(
            user_id="216746", api_key="secret", collection_key="PUBLICATIONS", opener=opener
        )

        self.assertEqual(exported, 101)
        self.assertEqual(sync_zotero.count_bibtex_entries(bibtex), 101)
        export_calls = [c for c in calls if c.get("format") == ["bibtex"]]
        self.assertEqual([len(c["itemKey"][0].split(",")) for c in export_calls], [50, 50, 1])
        self.assertEqual(calls[0]["format"], ["keys"])

    def test_rejects_an_incomplete_bibtex_export(self):
        def opener(request, timeout=30):
            query = parse_qs(urlparse(request.full_url).query)
            if query.get("format") == ["keys"]:
                return FakeResponse("ONE\nTWO\n")
            return FakeResponse("@article{one,\n  doi = {10.1/one}\n}\n")

        with self.assertRaisesRegex(ValueError, "expected 2 entries"):
            sync_zotero.fetch_bibtex(
                user_id="216746", api_key="secret", collection_key="PUBLICATIONS", opener=opener
            )

    def test_follows_pagination_links_within_a_key_batch(self):
        calls = []

        def opener(request, timeout=30):
            calls.append(request.full_url)
            if "format=keys" in request.full_url:
                return FakeResponse("ONE\nTWO\n")
            if "start=20" not in request.full_url:
                return FakeResponse(
                    "@article{one,\n  doi = {10.1/one}\n}\n",
                    {"Link": '<https://api.zotero.org/users/216746/items?start=20>; rel="next"'},
                )
            return FakeResponse("@article{two,\n  doi = {10.1/two}\n}\n")

        bibtex, exported = sync_zotero.fetch_bibtex(
            user_id="216746", api_key="secret", collection_key="PUBLICATIONS", opener=opener
        )
        self.assertEqual(exported, 2)
        self.assertEqual(sync_zotero.count_bibtex_entries(bibtex), 2)
        self.assertEqual(len(calls), 3)

    def test_rejects_changed_citation_keys_for_existing_dois(self):
        current = "@article{stable_key,\n  doi = {10.1/example}\n}\n"
        incoming = "@article{changed_key,\n  doi = {10.1/example}\n}\n"

        with self.assertRaisesRegex(ValueError, "citation key changed"):
            sync_zotero.validate_stable_keys(current, incoming)

    def test_rejects_an_export_that_removes_an_existing_entry(self):
        current = "@article{stable_key,\n  doi = {10.1/example}\n}\n"
        with self.assertRaisesRegex(ValueError, "missing existing citation key"):
            sync_zotero.validate_stable_keys(current, "")

    def test_allows_new_dois_and_preserves_existing_keys(self):
        current = "@article{stable_key,\n  doi = {10.1/example}\n}\n"
        incoming = (
            "@article{stable_key,\n  doi = {10.1/example}\n}\n"
            "@article{new_key,\n  doi = {10.1/new}\n}\n"
        )
        sync_zotero.validate_stable_keys(current, incoming)


if __name__ == "__main__":
    unittest.main()
