"""Unit tests for scripts/catalog.py.

Run from the repository root:
    python -m unittest tests.test_catalog -v
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("catalog", ROOT / "scripts" / "catalog.py")
catalog = importlib.util.module_from_spec(SPEC)
sys.modules["catalog"] = catalog
SPEC.loader.exec_module(catalog)


class ValidateRealCatalog(unittest.TestCase):
    def test_validate_zero_errors(self):
        problems = catalog.Problems()
        entries = catalog.load(problems, strict=True)
        self.assertGreater(len(entries), 1000)
        self.assertEqual(problems.errors, [], "\n".join(problems.errors))

    def test_all_category_files_present(self):
        files = {p.stem for p in catalog.table_files()}
        self.assertEqual(files, catalog.CATEGORY_SLUGS)

    def test_readme_links_every_category(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for slug in catalog.CATEGORY_SLUGS:
            self.assertIn(f"catalog/{slug}.md", readme)


class ParseHelpers(unittest.TestCase):
    def setUp(self):
        self._paths = []
    def tearDown(self):
        for p in self._paths:
            try:
                p.unlink()
            except FileNotFoundError:
                pass
    _counter = [0]
    def _write(self, content):
        self._counter[0] += 1
        p = ROOT / "catalog" / f"_test_tmp_{self._counter[0]}.md"
        p.write_text(content, encoding="utf-8")
        self._paths.append(p)
        return p

    def test_missing_header_is_error(self):
        p = self._write("# Title\n\nno table here\n")
        problems = catalog.Problems()
        entries = catalog.parse_file(p, problems)
        self.assertEqual(entries, [])
        self.assertTrue(any("missing table header" in e for e in problems.errors))

    def test_bad_column_count(self):
        content = (
            "# T\n\n"
            + catalog.HEADER + "\n"
            + catalog.DIVIDER + "\n"
            + "| [X](https://x.com) | API | desc | Free | None | - | - | editorial | - | extra |\n"
        )
        p = self._write(content)
        problems = catalog.Problems()
        catalog.parse_file(p, problems)
        self.assertTrue(any("expected 9 columns" in e for e in problems.errors))

    def test_unknown_type(self):
        content = (
            "# T\n\n"
            + catalog.HEADER + "\n"
            + catalog.DIVIDER + "\n"
            + "| [X](https://x.com) | Widget | desc text here long enough | Free | None | - | - | editorial | - |\n"
        )
        p = self._write(content)
        problems = catalog.Problems()
        catalog.parse_file(p, problems)
        self.assertTrue(any("unknown type" in e for e in problems.errors))

    def test_alphabetical_order_enforced(self):
        content = (
            "# T\n\n"
            + catalog.HEADER + "\n"
            + catalog.DIVIDER + "\n"
            + "| [Zebra](https://z.com) | API | zebra desc text here | Free | None | - | - | editorial | - |\n"
            + "| [Apple](https://a.com) | API | apple desc text here | Free | None | - | - | editorial | - |\n"
        )
        p = self._write(content)
        problems = catalog.Problems()
        catalog.parse_file(p, problems)
        self.assertTrue(any("not alphabetical" in e for e in problems.errors))

    def test_duplicate_name_detected(self):
        content = (
            "# T\n\n"
            + catalog.HEADER + "\n"
            + catalog.DIVIDER + "\n"
            + "| [Foo](https://foo.com) | API | foo desc text here | Free | None | - | - | editorial | - |\n"
            + "| [Foo](https://foo2.com) | API | foo2 desc text here | Free | None | - | - | editorial | - |\n"
        )
        p = self._write(content)
        problems = catalog.Problems()
        catalog.parse_file(p, problems)
        self.assertTrue(any("duplicate name" in e for e in problems.errors))


if __name__ == "__main__":
    unittest.main()
