from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


discovery = load_module("discover_publications", ROOT / "scripts" / "discover_publications.py")
generator = load_module("generate_publications_yml", ROOT / "scripts" / "generate_publications_yml.py")


class PublicationDiscoveryTests(unittest.TestCase):
    def test_normalizes_doi_forms(self):
        expected = "10.1016/j.example.2026.1"
        for raw in [
            expected,
            "doi:" + expected.upper(),
            "https://doi.org/" + expected,
            "http://dx.doi.org/" + expected,
        ]:
            self.assertEqual(discovery.normalize_doi(raw), expected)

    def test_keeps_only_crossref_validated_new_records(self):
        works = [
            {
                "id": "https://openalex.org/W1",
                "doi": "https://doi.org/10.1/new",
                "display_name": "A genuinely new paper",
                "publication_date": "2026-07-01",
                "type": "article",
                "authorships": [{"author": {"id": "https://openalex.org/A1"}}],
                "primary_location": {"source": {"display_name": "Journal"}},
            },
            {
                "id": "https://openalex.org/W2",
                "doi": "https://doi.org/10.1/already-known",
                "display_name": "Already known",
                "publication_date": "2026-06-01",
                "type": "article",
                "authorships": [{"author": {"id": "https://openalex.org/A1"}}],
            },
            {
                "id": "https://openalex.org/W3",
                "doi": "https://doi.org/10.1/excluded",
                "display_name": "Excluded working paper",
                "publication_date": "2026-06-01",
                "type": "article",
                "authorships": [{"author": {"id": "https://openalex.org/A1"}}],
            },
        ]
        crossref = {
            "10.1/new": {"title": ["A genuinely new paper"], "author": [{"family": "Lovelace", "given": "Robin"}]},
            "10.1/excluded": {"title": ["Excluded working paper"], "author": [{"family": "Lovelace", "given": "Robin"}]},
        }
        found = discovery.select_candidates(
            works,
            {"10.1/already-known"},
            {"known title"},
            {
                "excluded_title_regex": ["working paper"],
                "ignored_dois": [],
                "required_author_family_name": "Lovelace",
                "minimum_title_similarity": 0.9,
            },
            lambda doi: crossref.get(doi),
        )
        self.assertEqual([item["doi"] for item in found], ["10.1/new"])
        self.assertEqual(found[0]["provenance"]["crossref"], True)

    def test_rejects_crossref_records_without_required_author_or_ignored_doi(self):
        work = {
            "id": "https://openalex.org/W1", "doi": "https://doi.org/10.1/new",
            "display_name": "A genuinely new paper", "publication_date": "2026-07-01",
            "type": "article", "authorships": [], "primary_location": {"source": {}},
        }
        crossref = {"title": ["A genuinely new paper"], "author": [{"family": "Other"}]}
        config = {"required_author_family_name": "Lovelace", "minimum_title_similarity": 0.9}
        self.assertEqual(discovery.select_candidates([work], set(), set(), config, lambda _: crossref), [])
        crossref["author"] = [{"family": "Lovelace"}]
        config["ignored_dois"] = ["10.1/new"]
        self.assertEqual(discovery.select_candidates([work], set(), set(), config, lambda _: crossref), [])

    def test_zotero_entry_wins_over_discovered_duplicate(self):
        canonical = [{"key": "zotero", "doi": "10.1/same", "title": "Canonical", "year": 2026}]
        discovered = [{"key": "oa", "doi": "https://doi.org/10.1/same", "title": "Provisional", "year": 2026}]
        merged = generator.merge_discovered_entries(canonical, discovered)
        self.assertEqual(merged, canonical)

    def test_discovered_entry_without_page_links_to_doi(self):
        canonical = []
        discovered = [{"key": "oa", "doi": "10.1/new", "title": "Provisional", "year": 2026, "type": "Journal Article"}]
        merged = generator.merge_discovered_entries(canonical, discovered)
        self.assertEqual(merged[0]["path"], "https://doi.org/10.1/new")
        self.assertEqual(merged[0]["type"], "Journal Article (provisional)")


if __name__ == "__main__":
    unittest.main()
