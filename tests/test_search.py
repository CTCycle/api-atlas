import shutil
import tempfile
import unittest
from pathlib import Path

from regipy import models, search, store as store_module

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


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.root, self.tmp = make_root()
        self.addCleanup(self.tmp.cleanup)
        self.store = store_module.Store(self.root)
        self.store.load()

        records = []
        r1 = models.new_record(
            kind="api",
            name="Alpha Finance API",
            source="test",
            website="https://alpha.example.com",
            category="finance",
            pricing_model="free",
            level="imported",
            description="Free finance data endpoint",
            tags=["finance", "markets"],
            formats=["json"],
        )
        r1["verification"]["last_verified"] = "2025-01-01"
        r1["verification"]["confidence"] = "verified"
        r1["status"] = "active"
        records.append(r1)

        r2 = models.new_record(
            kind="dataset",
            name="Beta Climate Dataset",
            source="test",
            website="https://beta.example.com/data.csv",
            category="weather-climate",
            pricing_model="freemium",
            level="imported",
            description="Climate observations",
            tags=["climate"],
            formats=["csv", "json"],
        )
        r2["verification"]["last_verified"] = "2026-02-02"
        r2["verification"]["confidence"] = "partial"
        r2["status"] = "active"
        records.append(r2)

        r3 = models.new_record(
            kind="api",
            name="Gamma Unavailable",
            source="test",
            website="https://gamma.example.com",
            category="finance",
            pricing_model="paid",
            level="imported",
            description="Unavailable service",
            tags=["finance"],
            formats=["xml"],
        )
        r3["verification"]["last_verified"] = None
        r3["verification"]["confidence"] = "imported"
        r3["status"] = "unavailable"
        records.append(r3)

        for record in records:
            self.store.upsert(record)
        self.store.save()
        self.db = self.root / "index.sqlite"
        search.build_index(self.store, self.db)

    def test_text_search(self):
        results = search.query(self.db, text="Climate")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Beta Climate Dataset")

    def test_category_and_pricing(self):
        results = search.query(self.db, category="finance", pricing="free")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alpha Finance API")

    def test_exclusion(self):
        results = search.query(self.db, status="!unavailable")
        names = {row["name"] for row in results}
        self.assertNotIn("Gamma Unavailable", names)
        self.assertEqual(len(results), 2)

    def test_verified_since(self):
        results = search.query(self.db, verified_since="2026-01-01")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Beta Climate Dataset")

    def test_limit_offset(self):
        first = search.query(self.db, limit=1, offset=0, order="name")
        second = search.query(self.db, limit=1, offset=1, order="name")
        self.assertEqual(len(first), 1)
        self.assertEqual(len(second), 1)
        self.assertNotEqual(first[0]["id"], second[0]["id"])

    def test_data_format_and_count(self):
        results = search.query(self.db, data_format="csv")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Beta Climate Dataset")
        self.assertEqual(search.count(self.db, data_format="csv"), len(results))

    def test_index_helpers(self):
        self.assertTrue(search.index_exists(self.db))
        self.assertIsNotNone(search.index_age_hours(self.db))
        path = search.ensure_index(store=self.store, db_path=self.db, max_age_hours=24)
        self.assertEqual(path, str(self.db))


if __name__ == "__main__":
    unittest.main()
