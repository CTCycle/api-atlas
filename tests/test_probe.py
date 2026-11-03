"""Unit tests for scripts/probe.py.

The network is never touched: catalog._fetch is replaced with a routing stub.
Run from the repository root:
    python -m unittest tests.test_catalog tests.test_probe -v
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


catalog = _load("catalog")
probe = _load("probe")

JSON_SPEC = b'{"openapi": "3.0.0", "info": {"title": "Example"}, "paths": {"/a": {}}}'
YAML_SPEC = b"openapi: 3.0.0\ninfo:\n  title: Example\npaths:\n  /a:\n    get: {}\n"
HTML_DOCS = b'<html><body><a href="api/openapi.json">spec</a></body></html>'


class StubFetch:
    """Routes URLs to canned (status, headers, body) responses."""

    def __init__(self, routes):
        self.routes = routes
        self.calls = []

    def __call__(self, url, method="GET", timeout=15.0, read_body=False, insecure=False):
        self.calls.append(url)
        status, headers, body = self.routes.get(url, (404, {}, b"not found"))
        return status, headers, body, None


def entry(url, docs=None):
    return types.SimpleNamespace(name="Example", category="demo", type="API",
                                 url=url, docs=docs)


class ProbeCases(unittest.TestCase):
    def setUp(self):
        self._real_fetch = catalog._fetch

    def tearDown(self):
        catalog._fetch = self._real_fetch

    def test_docs_url_that_is_a_spec_is_probed(self):
        """A docs URL pointing straight at /openapi.json must be a candidate."""
        stub = StubFetch({
            "https://example.com": (200, {}, b"<html>home</html>"),
            "https://example.com/v1/openapi.json": (200, {}, JSON_SPEC),
        })
        catalog._fetch = stub
        record = probe.probe(entry("https://example.com",
                                   docs="https://example.com/v1/openapi.json"))
        self.assertIsNotNone(record["spec"], "spec at the docs URL was missed")
        self.assertEqual(record["spec"]["spec_url"], "https://example.com/v1/openapi.json")
        self.assertEqual(record["spec"]["path_count"], 1)

    def test_spec_behind_redirect_is_followed(self):
        """A spec served through a 301 must validate at the final URL."""
        stub = StubFetch({
            "https://example.com": (200, {}, b"<html>home</html>"),
            "https://example.com/openapi.json": (301, {"location": "/specs/v2.json"}, b""),
            "https://example.com/specs/v2.json": (200, {}, JSON_SPEC),
        })
        catalog._fetch = stub
        spec = probe.validate_spec("https://example.com/openapi.json")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["spec_url"], "https://example.com/specs/v2.json")

    def test_relative_links_resolve_against_final_url(self):
        """Links on a redirected page resolve against where the page landed."""
        stub = StubFetch({
            "https://example.com": (301, {"location": "/docs/"}, b""),
            "https://example.com/docs/": (200, {}, HTML_DOCS),
            "https://example.com/docs/api/openapi.json": (200, {}, JSON_SPEC),
        })
        catalog._fetch = stub
        urls = probe.candidate_spec_urls(entry("https://example.com"))
        self.assertIn("https://example.com/docs/api/openapi.json", urls)
        # discovered links rank before conventional guesses; the bare
        # /api/openapi.json entry comes from CONVENTIONAL, not from the page
        self.assertLess(urls.index("https://example.com/docs/api/openapi.json"),
                        urls.index("https://example.com/api/openapi.json"))

    def test_yaml_spec_is_parsed_when_pyyaml_is_available(self):
        try:
            import yaml  # noqa: F401
        except ImportError:
            self.skipTest("PyYAML not installed; YAML candidates are skipped by design")
        stub = StubFetch({"https://example.com/openapi.yaml": (200, {}, YAML_SPEC)})
        catalog._fetch = stub
        spec = probe.validate_spec("https://example.com/openapi.yaml")
        self.assertIsNotNone(spec)
        self.assertEqual(spec["spec_version"], "3.0.0")

    def test_html_and_empty_paths_are_rejected(self):
        stub = StubFetch({
            "https://example.com/docs": (200, {}, HTML_DOCS),
            "https://example.com/empty.json": (200, {},
                                               b'{"openapi": "3.0.0", "paths": {}}'),
        })
        catalog._fetch = stub
        self.assertIsNone(probe.validate_spec("https://example.com/docs"))
        self.assertIsNone(probe.validate_spec("https://example.com/empty.json"))


if __name__ == "__main__":
    unittest.main()
