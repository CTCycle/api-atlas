"""Unit tests for dedupe module."""

import tempfile
import unittest
from pathlib import Path

from regipy.models import new_record, normalize_record
from regipy.store import Store
from regipy import dedupe


def _insert(store, rec):
    rec = normalize_record(rec)
    store.records[rec["id"]] = rec
    return rec


def _make_records():
    r1 = new_record(kind="api", name="Foo Bar", source="test",
                    website="https://example.com/foo", category="unknown",
                    provider_name="Example")
    r1["provider"] = {"id": "example.com", "name": "Example",
                       "domain": "example.com"}
    r1["id"] = "example.com/foo-bar"
    r2 = new_record(kind="api", name="Foo Bar API", source="test",
                    website="https://example.com/foo", category="unknown",
                    provider_name="Example")
    r2["provider"] = {"id": "example.com", "name": "Example",
                       "domain": "example.com"}
    r2["id"] = "example.com/foo-bar-service"
    r3 = new_record(kind="api", name="Unrelated Service", source="test",
                    website="https://other.com", category="unknown",
                    provider_name="Other")
    r3["provider"] = {"id": "other.com", "name": "Other",
                       "domain": "other.com"}
    r3["id"] = "other.com/unrelated"
    return r1, r2, r3


class DedupeTests(unittest.TestCase):
    def _store_with(self, recs):
        tmp = tempfile.mkdtemp()
        root = Path(tmp)
        store = Store(root=root)
        store.load()
        for r in recs:
            _insert(store, r)
        store.save()
        store2 = Store(root=root)
        store2.load()
        return store2, tmp

    def test_finds_same_provider_near_identical(self):
        r1, r2, r3 = _make_records()
        store, _ = self._store_with([r1, r2, r3])
        pairs = dedupe.find_duplicates(store)
        self.assertTrue(len(pairs) >= 1)
        foo_ids = sorted(r["id"] for r in store.all() if "foo" in r["id"])
        self.assertEqual(len(foo_ids), 2)
        pair = (foo_ids[0], foo_ids[1])
        normalized = {(min(p["a"], p["b"]), max(p["a"], p["b"])) for p in pairs}
        self.assertIn(pair, normalized)

    def test_ignores_unrelated(self):
        r1, r2, r3 = _make_records()
        store, _ = self._store_with([r1, r2, r3])
        pairs = dedupe.find_duplicates(store)
        self.assertEqual(len(pairs), 1)

    def test_apply_merges_keeps_curated_and_alias(self):
        r1, r2, _ = _make_records()
        # make r1 curated
        r1["description"] = "Curated description"
        r1["curation"] = {"level": "curated", "updated": "2026-01-01"}
        r2["curation"] = {"level": "imported", "updated": "2026-01-01"}
        store, _ = self._store_with([r1, r2])
        pairs = dedupe.find_duplicates(store)
        self.assertTrue(len(pairs) >= 1)
        summary = dedupe.apply_merges(store, pairs)
        self.assertEqual(summary["merged"], 1)
        self.assertEqual(len(store.all()), 1)
        winner = store.all()[0]
        self.assertEqual(winner["curation"]["level"], "curated")
        self.assertEqual(winner["description"], "Curated description")
        self.assertTrue(len(winner.get("aliases") or []) >= 1)

    def test_name_similarity(self):
        self.assertGreater(dedupe.name_similarity("Foo Bar", "Foo Bar Baz"), 0.5)
        self.assertEqual(dedupe.name_similarity("", ""), 1.0)

    def test_pair_score(self):
        r1 = {"name": "Foo", "urls": {"website": "https://example.com/a"}}
        r2 = {"name": "Foo", "urls": {"website": "https://example.com/b"}}
        self.assertGreaterEqual(dedupe.pair_score(r1, r2), 0.0)

    def test_cross_provider_identical(self):
        r1, _, _ = _make_records()
        r4 = new_record(kind="api", name="Foo Bar", source="test",
                        website="https://other.com/foo", category="unknown",
                        provider_name="Other")
        r4["provider"] = {"id": "other.com", "name": "Other", "domain": "other.com"}
        r4["id"] = "other.com/foo-bar"
        store, _ = self._store_with([r1, r4])
        pairs = dedupe.find_duplicates(store, include_cross_provider=True)
        self.assertTrue(any(p["reason"] == "identical_name_different_provider"
                            for p in pairs))


if __name__ == "__main__":
    unittest.main()
