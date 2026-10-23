"""Pipeline tests: parsing, normalisation, merge precedence, idempotency."""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from regipy import ids, importers, models, schema
from regipy.store import Store

REPO = Path(__file__).resolve().parent.parent

PUBLIC_APIS_SAMPLE = """\
# Title

## APILayer APIs

| [Sponsored](https://sponsor.example/) | Ad slot | No | Yes | No |

### Weather

API | Description | Auth | HTTPS | CORS
|:---|:---|:---|:---|:---|
| [Open-Meteo](https://open-meteo.com/) | Free weather forecast API | No | Yes | Yes |
| [WeatherAPI](https://www.weatherapi.com/) | Weather and astronomy | `apiKey` | Yes | Unknown |
| [Broken Row](https://broken.example/) | Missing https column |

### Animals

| [Cat Facts](https://catfact.ninja/) | Random cat facts | No | Yes | Yes |
"""

AWESOME_SAMPLE = """\
Awesome Public Datasets
=======================

Climate+Weather
---------------

* |OK_ICON| `NOAA GHCN Daily - Daily climate observations from thousands of stations <https://www.ncei.noaa.gov/products/land-based-station/global-historical-climatology-network-daily>`_ [`Meta <https://github.com/awesomedata/apd-core/tree/master/core/Climate+Weather/NOAA-GHCN-Daily.yml>`_]
* |FIXME_ICON| `Broken Entry <https://example.org/dataset.csv>`_ [`Meta <https://github.com/awesomedata/apd-core/tree/master/core/Climate+Weather/Broken.yml>`_]
"""

APIS_GURU_SAMPLE = {
    "example.com": {
        "added": "2020-01-01T00:00:00.000Z",
        "preferred": "1.0.0",
        "versions": {
            "1.0.0": {
                "info": {
                    "title": "Example Weather API",
                    "description": "Weather [forecasts](https://example.com) for the world.",
                    "version": "1.0.0",
                    "contact": {"url": "https://example.com"},
                    "license": {"name": "Apache 2.0", "url": "https://example.com/license"},
                    "x-apisguru-categories": ["open_data", "weather"],
                    "x-providerName": "example.com",
                },
                "swaggerUrl": "https://api.apis.guru/v2/specs/example.com/1.0.0/swagger.json",
                "openapiVer": "3.0.1",
            }
        },
    }
}


def make_root() -> Path:
    root = Path(tempfile.mkdtemp(prefix="regipy-test-"))
    shutil.copytree(REPO / "schema", root / "schema")
    (root / "catalog").mkdir()
    return root


class ParserTests(unittest.TestCase):
    def test_public_apis_rows_and_sections(self):
        records = importers.public_apis.parse(PUBLIC_APIS_SAMPLE)
        names = [r["name"] for r in records]
        self.assertEqual(names, ["Open-Meteo", "WeatherAPI", "Cat Facts"])
        self.assertNotIn("Sponsored", names)
        self.assertEqual(records[0]["category"], "weather-climate")
        self.assertEqual(records[0]["access"]["model"], "public")
        self.assertEqual(records[1]["access"]["model"], "api_key")
        self.assertEqual(records[1]["technical"]["cors"], "unknown")
        self.assertEqual(records[2]["category"], "animals")
        self.assertTrue(records[0]["pricing"]["free_tier_indicated"])
        self.assertEqual(records[0]["verification"]["confidence"], "imported")

    def test_awesome_datasets_bullets(self):
        records = importers.awesome_datasets.parse(AWESOME_SAMPLE)
        self.assertEqual(len(records), 2)
        first = records[0]
        self.assertEqual(first["kind"], "dataset")
        self.assertEqual(first["category"], "weather-climate")
        self.assertEqual(first["name"], "NOAA GHCN Daily")
        self.assertIn("Daily climate observations", first["description"])
        self.assertEqual(first["type"], "dataset")
        self.assertEqual(first["urls"]["website"],
                         "https://www.ncei.noaa.gov/products/land-based-station/"
                         "global-historical-climatology-network-daily")
        self.assertEqual(records[1]["type"], "download")
        self.assertEqual(first["provenance"][0]["upstream_id"],
                         "Climate+Weather/NOAA-GHCN-Daily.yml")

    def test_apis_guru_record(self):
        records = importers.apis_guru.parse(APIS_GURU_SAMPLE, version="abc123")
        self.assertEqual(len(records), 1)
        rec = records[0]
        self.assertEqual(rec["type"], "openapi")
        self.assertEqual(rec["category"], "open-data")
        self.assertEqual(rec["license"]["name"], "Apache 2.0")
        self.assertEqual(rec["license"]["basis"], "upstream_catalog")
        self.assertTrue(rec["urls"]["spec"].endswith("swagger.json"))
        self.assertNotIn("[forecasts]", rec["description"])
        self.assertEqual(rec["provider"]["id"], "example.com")

    def test_curated_seed_file(self):
        root = make_root()
        try:
            seeds = root / "curation" / "seeds"
            seeds.mkdir(parents=True)
            (seeds / "01-test.yaml").write_text(
                "version: 1\nsource: curated\nentries:\n"
                "  - name: Example Data Portal\n"
                "    kind: dataset\n"
                "    category: government\n"
                "    description: A portal.\n"
                "    provider: data.example.gov\n"
                "    website: https://data.example.gov/\n"
                "    access: public\n"
                "    pricing: free\n"
                "    pricing_basis: official_docs\n"
                "    license: CC BY 4.0\n"
                "    license_spdx: CC-BY-4.0\n"
                "    commercial_use: allowed\n"
                "    confidence: verified\n"
                "    verified_on: '2026-01-02'\n",
                encoding="utf-8",
            )
            records = importers.curated.parse_dir(seeds)
            self.assertEqual(len(records), 1)
            rec = records[0]
            self.assertEqual(rec["curation"]["level"], "curated")
            self.assertEqual(rec["verification"]["confidence"], "verified")
            self.assertEqual(rec["verification"]["last_verified"], "2026-01-02")
            self.assertEqual(rec["status"], "active")
            self.assertEqual(schema.validate_record(rec), [])
        finally:
            shutil.rmtree(root, ignore_errors=True)


class IdentityTests(unittest.TestCase):
    def test_hosted_pages_keep_project_segment(self):
        provider, domain = ids.provider_identity("https://alexwohlbruck.github.io/cat-facts/")
        self.assertEqual(provider, "alexwohlbruck.github.io")
        self.assertEqual(domain, "alexwohlbruck.github.io")

    def test_registrable_domain(self):
        self.assertEqual(ids.registrable_domain("api.example.co.uk"), "example.co.uk")
        self.assertEqual(ids.registrable_domain("api.openweathermap.org"), "openweathermap.org")

    def test_url_normalisation_drops_tracking(self):
        self.assertEqual(ids.normalize_url("http://Example.com/path/?utm_source=x&a=1#frag"),
                         "http://example.com/path?a=1")

    def test_slugify_handles_non_ascii(self):
        self.assertEqual(ids.slugify("Datos Abiertos"), "datos-abiertos")
        self.assertTrue(ids.slugify("数据").startswith("entry-"))


class MergeTests(unittest.TestCase):
    def setUp(self):
        self.root = make_root()
        self.store = Store(self.root).load()

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _imported(self, name="Example Weather", **kwargs):
        base = dict(kind="api", name=name, source="public-apis", website="https://example.com/",
                    category="weather-climate", pricing_model="unknown")
        base.update(kwargs)
        return models.new_record(**base)

    def test_reimport_is_idempotent(self):
        self.assertEqual(self.store.upsert(self._imported()), "added")
        self.assertEqual(self.store.upsert(self._imported()), "unchanged")

    def test_curated_beats_imported_and_records_conflict(self):
        self.store.upsert(self._imported())
        curated = models.new_record(kind="api", name="Example Weather", source="curated",
                                    website="https://example.com/", category="weather-climate",
                                    pricing_model="freemium", pricing_basis="official_docs",
                                    level="curated", status="active", method="manual_review",
                                    confidence="partial")
        self.assertEqual(self.store.upsert(curated), "merged")
        rec = self.store.get("example.com/example-weather")
        self.assertEqual(rec["pricing"]["model"], "freemium")
        self.assertEqual(rec["curation"]["level"], "curated")
        self.assertEqual(len(rec["provenance"]), 2)
        self.assertTrue(rec["conflicts"])

    def test_import_does_not_reset_verification(self):
        self.store.upsert(self._imported())
        rec = self.store.get("example.com/example-weather")
        rec["verification"].update({"method": "http_head", "confidence": "partial",
                                    "last_verified": "2026-01-01", "last_checked": "2026-01-01"})
        rec["status"] = "active"
        self.store.upsert(self._imported(description="A new description from upstream"))
        rec = self.store.get("example.com/example-weather")
        self.assertEqual(rec["verification"]["last_verified"], "2026-01-01")
        self.assertEqual(rec["status"], "active")
        self.assertIn("new description", rec["description"])

    def test_save_and_reload_roundtrip(self):
        self.store.upsert(self._imported())
        self.store.upsert(models.new_record(kind="dataset", name="Some Dataset", source="curated",
                                            website="https://data.example.org/csv",
                                            category="economics", level="curated"))
        saved = self.store.save()
        self.assertEqual(saved["records"], 2)
        reloaded = Store(self.root).load()
        self.assertEqual(len(reloaded.all()), 2)
        self.assertTrue((self.root / "catalog" / "apis" / "weather-climate.jsonl").exists())
        self.assertTrue((self.root / "catalog" / "datasets" / "economics.jsonl").exists())

    def test_category_change_moves_shard(self):
        self.store.upsert(self._imported())
        rec = self.store.get("example.com/example-weather")
        rec["category"] = "finance"
        self.store.save()
        self.assertFalse((self.root / "catalog" / "apis" / "weather-climate.jsonl").exists())
        self.assertTrue((self.root / "catalog" / "apis" / "finance.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
