import json
import shutil
import tempfile
import unittest
from pathlib import Path

from regipy import models, store as store_module

REPO_ROOT = Path(__file__).resolve().parents[1]


def make_root():
    tmp = tempfile.TemporaryDirectory()
    root = Path(tmp.name)
    (root / "schema").mkdir()
    for path in (REPO_ROOT / "schema").iterdir():
        if path.is_file():
            shutil.copy2(path, root / "schema" / path.name)
    (root / "catalog").mkdir()
    return root, tmp


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.root, self.tmp = make_root()
        self.addCleanup(self.tmp.cleanup)

    def _record(self, **kwargs):
        defaults = dict(
            kind="api",
            name="Example API",
            source="test",
            website="https://example.com/api",
            category="finance",
            pricing_model="free",
            level="imported",
        )
        defaults.update(kwargs)
        return models.new_record(**defaults)

    def test_roundtrip(self):
        store = store_module.Store(self.root)
        store.load()
        record = self._record()
        store.upsert(record)
        store.save()

        loaded = store_module.Store(self.root)
        loaded.load()
        self.assertEqual(len(loaded.records), 1)
        self.assertEqual(loaded.all()[0]["name"], "Example API")
        self.assertEqual(loaded.all()[0]["id"], record["id"])

    def test_idempotent_reupsert(self):
        store = store_module.Store(self.root)
        store.load()
        record = self._record()
        self.assertEqual(store.upsert(record), "added")
        self.assertEqual(store.upsert(record), "unchanged")

    def test_curated_beats_imported(self):
        store = store_module.Store(self.root)
        store.load()
        imported = self._record(description="short", level="imported")
        store.upsert(imported)
        curated = self._record(description="a much longer curated description", level="curated")
        curated["license"]["name"] = "MIT"
        curated["license"]["spdx"] = "MIT"
        status = store.upsert(curated)
        self.assertEqual(status, "merged")
        saved = store.get(store.all()[0]["id"])
        self.assertEqual(saved["curation"]["level"], "curated")
        self.assertEqual(saved["license"]["spdx"], "MIT")
        self.assertIn("much longer", saved["description"])

    def test_provenance_accumulates(self):
        store = store_module.Store(self.root)
        store.load()
        first = self._record(source="source-a")
        store.upsert(first)
        second = self._record(source="source-b")
        store.upsert(second)
        saved = store.all()[0]
        sources = [item["source"] for item in saved["provenance"]]
        self.assertIn("source-a", sources)
        self.assertIn("source-b", sources)
        self.assertEqual(len(saved["provenance"]), 2)

    def test_category_change_moves_shard(self):
        store = store_module.Store(self.root)
        store.load()
        record = self._record(category="finance")
        store.upsert(record)
        store.save()
        old_path = self.root / "catalog" / "apis" / "finance.jsonl"
        self.assertTrue(old_path.exists())

        moved = self._record(category="health-medical", level="curated")
        # Keep the same id/provider identity by copying id from stored record.
        moved["id"] = store.all()[0]["id"]
        store.upsert(moved)
        store.save()
        new_path = self.root / "catalog" / "apis" / "health-medical.jsonl"
        self.assertTrue(new_path.exists())
        self.assertFalse(old_path.exists())


if __name__ == "__main__":
    unittest.main()
