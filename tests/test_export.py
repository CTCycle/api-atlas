import csv
import io
import json
import tempfile
import unittest
from pathlib import Path

from regipy import export, models

REPO_ROOT = Path(__file__).resolve().parents[1]


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.records = [
            models.new_record(
                kind="api",
                name="Example, API",
                source="test",
                website="https://example.com",
                category="finance",
                description="Has a, comma",
                pricing_model="free",
                free_tier_indicated=True,
                free_tier_limits="100/day",
                tags=["a", "b"],
                formats=["json"],
            )
        ]
        self.records[0]["verification"]["last_verified"] = "2026-01-01"

    def test_csv_roundtrip_quoted_commas(self):
        text = export.to_csv(self.records)
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        self.assertEqual(len(rows), 2)
        header = rows[0]
        data = rows[1]
        name_index = header.index("name")
        desc_index = header.index("description")
        self.assertEqual(data[name_index], "Example, API")
        self.assertEqual(data[desc_index], "Has a, comma")

    def test_jsonl_line_count(self):
        text = export.to_jsonl(self.records)
        lines = [line for line in text.splitlines() if line.strip()]
        self.assertEqual(len(lines), len(self.records))
        for line in lines:
            json.loads(line)

    def test_json_parse(self):
        text = export.to_json(self.records)
        parsed = json.loads(text)
        self.assertEqual(len(parsed), len(self.records))
        self.assertEqual(parsed[0]["name"], "Example, API")

    def test_markdown_table_shape(self):
        text = export.to_markdown(self.records)
        lines = text.strip().splitlines()
        self.assertGreaterEqual(len(lines), 3)
        self.assertTrue(lines[0].startswith("|"))
        self.assertTrue(set(lines[1].replace(" ", "")) <= set("|-"))
        self.assertEqual(len(lines), 3)

    def test_export_creates_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "nested" / "out.csv"
            returned = export.export(self.records, fmt="csv", out=out)
            self.assertTrue(out.exists())
            self.assertEqual(out.read_text(encoding="utf-8"), returned)


if __name__ == "__main__":
    unittest.main()
