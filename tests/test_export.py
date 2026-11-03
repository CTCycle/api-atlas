"""Tests for the committed machine-readable exports.

The JSON Schema under data/ is published as a contract for consumers, so the
exports must satisfy it without pulling in a validator dependency. The checks here
are the subset of JSON Schema 2020-12 the schema actually uses.

Run from the repository root:
    python -m unittest tests.test_catalog tests.test_probe tests.test_export -v
"""
import csv
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _load_catalog():
    if "catalog" in sys.modules:
        return sys.modules["catalog"]
    spec = importlib.util.spec_from_file_location("catalog", ROOT / "scripts" / "catalog.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules["catalog"] = module
    spec.loader.exec_module(module)
    return module


catalog = _load_catalog()
SCHEMA = json.loads((DATA / "catalog.schema.json").read_text(encoding="utf-8"))
ROWS = [json.loads(line) for line in
        (DATA / "catalog.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
ARRAY = json.loads((DATA / "catalog.json").read_text(encoding="utf-8"))


def schema_errors(value, schema, path="$"):
    """Return a list of human-readable violations of the subset used by the schema."""
    errors = []
    kinds = schema.get("type")
    if kinds:
        kinds = kinds if isinstance(kinds, list) else [kinds]

        def matches(kind):
            if kind == "string":
                return isinstance(value, str)
            if kind == "boolean":
                return isinstance(value, bool)
            if kind == "object":
                return isinstance(value, dict)
            if kind == "array":
                return isinstance(value, list)
            if kind == "null":
                return value is None
            return True

        if not any(matches(kind) for kind in kinds):
            errors.append(f"{path}: expected {kinds}, got {type(value).__name__}")
            return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: {value!r} not in {schema['enum']}")

    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: shorter than minLength {schema['minLength']}")
        if "maxLength" in schema and len(value) > schema["maxLength"]:
            errors.append(f"{path}: longer than maxLength {schema['maxLength']}")
        if "pattern" in schema and not re.search(schema["pattern"], value):
            errors.append(f"{path}: does not match {schema['pattern']!r}")

    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for name in schema.get("required", []):
            if name not in value:
                errors.append(f"{path}: missing required property {name!r}")
        if schema.get("additionalProperties") is False:
            for name in value:
                if name not in properties:
                    errors.append(f"{path}: unexpected property {name!r}")
        for name, child in properties.items():
            if name in value:
                errors.extend(schema_errors(value[name], child, f"{path}.{name}"))
    return errors


class Exports(unittest.TestCase):
    def test_json_and_jsonl_agree(self):
        self.assertEqual(ARRAY, ROWS, "data/catalog.json and data/catalog.jsonl disagree")

    def test_exports_match_catalog(self):
        entries = catalog.load(catalog.Problems(), strict=True)
        self.assertEqual(len(ROWS), len(entries))

    def test_ids_are_unique(self):
        ids = [row["id"] for row in ROWS]
        self.assertEqual(len(ids), len(set(ids)), "duplicate ids in the exports")

    def test_every_row_satisfies_the_published_schema(self):
        self.assertIn("schema", str(SCHEMA.get("$schema", "")))
        failures = []
        for row in ROWS:
            failures.extend(schema_errors(row, SCHEMA))
        self.assertEqual(failures, [], "\n".join(failures[:20]))

    def test_csv_matches_schema_fields(self):
        with (DATA / "catalog.csv").open(encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            header = reader.fieldnames
            rows = list(reader)
        self.assertEqual(header, list(SCHEMA["properties"]))
        self.assertEqual(len(rows), len(ROWS))
        first = rows[0]
        self.assertEqual(first["name"], ROWS[0]["name"])
        self.assertEqual(first["description"], ROWS[0]["description"])


if __name__ == "__main__":
    unittest.main()
