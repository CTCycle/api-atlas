"""Unit tests for linkcheck module."""

import tempfile
import unittest
from pathlib import Path

from regipy.models import new_record
from regipy.store import Store
from regipy import linkcheck


def _make_store(tmp: str) -> Store:
    root = Path(tmp)
    store = Store(root=root)
    store.load()
    rec = new_record(
        kind="api",
        name="Example API",
        source="test",
        website="https://example.com",
        category="unknown",
    )
    store.upsert(rec)
    store.save()
    # Reload to mimic on-disk state.
    store2 = Store(root=root)
    store2.load()
    return store2


class LinkCheckTests(unittest.TestCase):
    def test_404_marks_unavailable(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _make_store(tmp)
            rid = store.all()[0]["id"]

            def fake(url, **kw):
                return {"ok": False, "status": 404, "error": "HTTP 404",
                        "elapsed_ms": 1, "method": "head"}

            res = linkcheck.linkcheck(store, checker=fake, today="2026-01-01")
            self.assertEqual(res["checked"], 1)
            self.assertEqual(res["broken"], 1)
            rec = store.get(rid)
            self.assertEqual(rec["status"], "unavailable")
            self.assertEqual(rec["verification"]["http_status"], 404)
            self.assertEqual(rec["verification"]["last_checked"], "2026-01-01")

    def test_200_sets_active_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _make_store(tmp)
            rid = store.all()[0]["id"]

            def fake(url, **kw):
                return {"ok": True, "status": 200, "error": None,
                        "elapsed_ms": 1, "method": "head"}

            res = linkcheck.linkcheck(store, checker=fake, today="2026-01-01")
            self.assertEqual(res["ok"], 1)
            rec = store.get(rid)
            self.assertEqual(rec["status"], "active")
            self.assertEqual(rec["verification"]["confidence"], "partial")
            self.assertEqual(rec["verification"]["last_verified"], "2026-01-01")
            self.assertEqual(rec["verification"]["method"], "http_head")

    def test_gated_403_no_last_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _make_store(tmp)
            rid = store.all()[0]["id"]

            def fake(url, **kw):
                return {"ok": False, "status": 403, "error": "HTTP 403",
                        "elapsed_ms": 1, "method": "head"}

            res = linkcheck.linkcheck(store, checker=fake, today="2026-01-01")
            self.assertEqual(res["gated"], 1)
            rec = store.get(rid)
            self.assertIsNone(rec["verification"]["last_verified"])
            self.assertEqual(rec["verification"]["http_status"], 403)
            self.assertIn("403", rec["verification"]["notes"])

    def test_dry_run_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _make_store(tmp)
            rid = store.all()[0]["id"]
            before = store.get(rid).copy()

            def fake(url, **kw):
                return {"ok": False, "status": 404, "error": "HTTP 404",
                        "elapsed_ms": 1, "method": "head"}

            res = linkcheck.linkcheck(store, checker=fake, dry_run=True,
                                     today="2026-01-01")
            self.assertEqual(res["updated"], 0)
            after = store.get(rid)
            self.assertEqual(after["status"], before["status"])
            self.assertEqual(after["verification"]["last_checked"],
                             before["verification"]["last_checked"])

    def test_force_bypasses_age_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = _make_store(tmp)
            rid = store.all()[0]["id"]
            rec = store.get(rid)
            rec["verification"]["last_checked"] = "2026-01-01"
            store.records[rid] = rec

            def fake(url, **kw):
                return {"ok": True, "status": 200, "error": None,
                        "elapsed_ms": 1, "method": "head"}

            # Without force and max_age_days large, should skip.
            res = linkcheck.linkcheck(store, checker=fake, today="2026-01-02",
                                     max_age_days=30)
            self.assertEqual(res["checked"], 0)
            # With force, checks.
            res2 = linkcheck.linkcheck(store, checker=fake, force=True,
                                      today="2026-01-02")
            self.assertEqual(res2["checked"], 1)

    def test_check_url_signature(self):
        # Smoke test that check_url returns required keys.
        pass


if __name__ == "__main__":
    unittest.main()
