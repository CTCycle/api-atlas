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


class LinkCheckSemantics(unittest.TestCase):
    """The report proposes URL edits from redirect targets, so the checker must
    resolve relative Location headers and must not call a parked domain 'ok'."""

    def setUp(self):
        import unittest.mock as mock
        self.mock = mock
        self._sleep = mock.patch.object(catalog.time, "sleep", lambda *_: None)
        self._sleep.start()

    def tearDown(self):
        self._sleep.stop()

    def _fake(self, script):
        calls = []

        def fetch(url, method="GET", timeout=15.0, read_body=False):
            calls.append(url)
            status, headers, body = script[url]
            return status, headers, body, None
        return fetch, calls

    def _run(self, script, url, deep=False):
        fetch, calls = self._fake(script)
        with self.mock.patch.object(catalog, "_fetch", fetch):
            return catalog.check_url(url, deep=deep), calls

    def test_relative_location_is_resolved_to_absolute(self):
        script = {
            "https://sdmdataaccess.sc.egov.usda.gov/": (302, {"location": "/Help.aspx#JavaScript"}, b""),
            "https://sdmdataaccess.sc.egov.usda.gov/Help.aspx": (200, {}, b""),
        }
        result, _ = self._run(script, "https://sdmdataaccess.sc.egov.usda.gov/")
        self.assertEqual(result["kind"], "moved")
        self.assertTrue(result["ok"])
        self.assertTrue(result["final_url"].startswith("https://sdmdataaccess.sc.egov.usda.gov/"))
        self.assertNotIn("...", result["final_url"])

    def test_redirect_to_parking_host_is_dead(self):
        script = {
            "https://gone.example/": (301, {"location": "https://www.hugedomains.com/domain_profile.cfm"}, b""),
            "https://www.hugedomains.com/domain_profile.cfm": (200, {}, b""),
        }
        result, _ = self._run(script, "https://gone.example/")
        self.assertEqual(result["kind"], "dead-parked")
        self.assertFalse(result["ok"])

    def test_404_after_redirect_is_broken(self):
        script = {
            "https://old.example/docs": (301, {"location": "https://new.example/docs"}, b""),
            "https://new.example/docs": (404, {}, b""),
        }
        result, _ = self._run(script, "https://old.example/docs")
        self.assertEqual(result["kind"], "broken")

    def test_deep_check_detects_parked_page_text(self):
        body = b"<html><head><title>example.com</title></head><body>This domain is for sale</body></html>"
        script = {"https://example.com/": (200, {}, body)}
        result, _ = self._run(script, "https://example.com/", deep=True)
        self.assertEqual(result["kind"], "dead-parked")

    def test_headers_are_normalised_to_lowercase(self):
        class Fake:
            def items(self):
                return [("Location", "https://x.example/"), ("Content-Type", "text/html")]
        self.assertEqual(catalog._lower_headers(Fake())["location"], "https://x.example/")

    def test_registrable_domain_flags_offsite_moves(self):
        self.assertEqual(catalog._registrable("https://docs.example.co.uk/a"), "example.co.uk")
        self.assertEqual(catalog._registrable("https://api.example.com/x"), "example.com")
        script = {
            "https://gone.example/api": (301, {"location": "http://survey-twist.com"}, b""),
            "http://survey-twist.com": (200, {}, b""),
        }
        result, _ = self._run(script, "https://gone.example/api")
        self.assertTrue(result["moved_offsite"])

    def test_broken_chain_is_distinguished_from_refusal(self):
        calls = {"n": 0}

        def fetch(url, method="GET", timeout=15.0, read_body=False, insecure=False):
            calls["n"] += 1
            if not insecure:
                return None, {}, b"", "URLError: certificate verify failed"
            return 200, {}, b"<html><title>Fine</title></html>", None

        with self.mock.patch.object(catalog, "_fetch", fetch):
            result = catalog.check_url("https://chain.example/", deep=True)
        self.assertEqual(result["kind"], "tls-chain")
        self.assertTrue(result["ok"])

    def test_page_signals_extracts_title(self):
        title, hint = catalog.page_signals(
            b"<html><head><title>  Open-Meteo  API  </title></head><body>ok</body></html>")
        self.assertEqual(title, "Open-Meteo API")
        self.assertIsNone(hint)


if __name__ == "__main__":
    unittest.main()
