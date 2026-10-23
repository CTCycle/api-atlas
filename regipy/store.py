"""JSONL shard store: the catalog files are the source of truth."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from . import ids, models, schema

KIND_DIRS = {"api": "apis", "dataset": "datasets"}


def dumps(record: dict[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"))


class Store:
    """Loads, merges and persists catalog shards under catalog/<kind>/<category>.jsonl."""

    def __init__(self, root: Path | str | None = None):
        self.root = Path(root) if root else schema.repo_root()
        self.catalog_dir = self.root / "catalog"
        self.records: dict[str, dict[str, Any]] = {}
        self._by_key: dict[str, str] = {}
        self.dirty: set[str] = set()
        self.loaded = False

    # ---------------------------------------------------------------- loading
    def load(self) -> "Store":
        self.records.clear()
        self._by_key.clear()
        self.dirty.clear()
        for path in sorted(self.catalog_dir.glob("*/*.jsonl")):
            with path.open(encoding="utf-8") as handle:
                for lineno, line in enumerate(handle, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"{path}:{lineno}: invalid JSON: {exc}") from exc
                    rec = models.normalize_record(rec)
                    self.records[rec["id"]] = rec
                    self._by_key[self._key(rec)] = rec["id"]
        self.loaded = True
        return self

    @staticmethod
    def _key(rec: dict[str, Any]) -> str:
        domain = (rec.get("provider") or {}).get("domain") or (rec.get("provider") or {}).get("id")
        return ids.dedupe_key(domain, rec.get("name") or "")

    # ---------------------------------------------------------------- reading
    def all(self) -> list[dict[str, Any]]:
        return [self.records[key] for key in sorted(self.records)]

    def get(self, entry_id: str) -> dict[str, Any] | None:
        return self.records.get(entry_id)

    def find(self, needle: str) -> dict[str, Any] | None:
        """Exact id, else unique suffix match."""
        if needle in self.records:
            return self.records[needle]
        candidates = [rec for key, rec in self.records.items()
                      if key.endswith("/" + needle) or needle in key]
        return candidates[0] if len(candidates) == 1 else None

    def by_provider(self, provider: str) -> list[dict[str, Any]]:
        out = []
        for rec in self.all():
            prov = rec.get("provider") or {}
            if provider in (prov.get("id"), prov.get("domain"), prov.get("name")):
                out.append(rec)
        return out

    def stats(self) -> dict[str, Any]:
        recs = self.all()
        cats = schema.categories()
        by_category = Counter(r.get("category") for r in recs)
        by_kind = Counter(r.get("kind") for r in recs)
        by_pricing = Counter((r.get("pricing") or {}).get("model", "unknown") for r in recs)
        by_access = Counter((r.get("access") or {}).get("model", "unknown") for r in recs)
        by_confidence = Counter((r.get("verification") or {}).get("confidence") for r in recs)
        by_status = Counter(r.get("status") for r in recs)
        by_commercial = Counter((r.get("license") or {}).get("commercial_use", "unknown") for r in recs)
        providers = {(r.get("provider") or {}).get("id") for r in recs}
        flagged = sum(1 for r in recs if r.get("flags"))
        empty_categories = [c for c in cats if by_category.get(c, 0) == 0]
        return {
            "total": len(recs),
            "by_kind": dict(sorted(by_kind.items())),
            "by_category": dict(sorted(by_category.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_pricing": dict(sorted(by_pricing.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_access": dict(sorted(by_access.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_confidence": dict(sorted(by_confidence.items())),
            "by_status": dict(sorted(by_status.items())),
            "by_commercial_use": dict(sorted(by_commercial.items(), key=lambda kv: (-kv[1], kv[0]))),
            "providers": len({p for p in providers if p}),
            "flagged": flagged,
            "empty_categories": empty_categories,
            "coverage_ratio": round(len([c for c in cats if by_category.get(c)]) / max(len(cats), 1), 3),
        }

    # ---------------------------------------------------------------- writing
    def shard_path(self, rec: dict[str, Any]) -> Path:
        kind_dir = KIND_DIRS.get(rec.get("kind"), "apis")
        category = rec.get("category") or "unknown"
        return self.catalog_dir / kind_dir / f"{category}.jsonl"

    def upsert(self, record: dict[str, Any]) -> str:
        rec = models.normalize_record(record)
        if not (rec.get("provider") or {}).get("domain"):
            models.apply_provider_policy(rec, str(self.root))
        key = self._key(rec)
        target_id = self.records.get(rec["id"]) and rec["id"] or self._by_key.get(key) or rec["id"]
        if target_id != rec["id"]:
            rec.setdefault("aliases", [])
            if rec["id"] not in rec["aliases"]:
                rec["aliases"] = sorted({*rec.get("aliases", []), rec["id"]})
            rec["id"] = target_id
        existing = self.records.get(rec["id"])
        if existing is None:
            self.records[rec["id"]] = rec
            self._by_key[key] = rec["id"]
            self.dirty.add(rec["id"])
            return "added"
        merged, status = models.merge_into(existing, rec)
        if status == "unchanged":
            return "unchanged"
        self.records[merged["id"]] = merged
        self._by_key[self._key(merged)] = merged["id"]
        self.dirty.add(merged["id"])
        return status

    def add_many(self, records: Iterable[dict[str, Any]]) -> Counter:
        counter: Counter = Counter()
        for rec in records:
            counter[self.upsert(rec)] += 1
        return counter

    def remove(self, entry_id: str) -> bool:
        if entry_id not in self.records:
            return False
        rec = self.records.pop(entry_id)
        self._by_key.pop(self._key(rec), None)
        self.dirty.add(entry_id)
        return True

    def save(self) -> dict[str, int]:
        """Rewrite only shards whose serialised content changed."""
        groups: dict[Path, list[dict[str, Any]]] = {}
        for rec in self.records.values():
            groups.setdefault(self.shard_path(rec), []).append(rec)

        written = 0
        checked = 0
        for path, recs in groups.items():
            body = "".join(dumps(rec) + "\n" for rec in sorted(recs, key=lambda r: r["id"]))
            path.parent.mkdir(parents=True, exist_ok=True)
            checked += 1
            current = path.read_text(encoding="utf-8") if path.exists() else ""
            if current != body:
                path.write_text(body, encoding="utf-8")
                written += 1

        removed = 0
        for path in self.catalog_dir.glob("*/*.jsonl"):
            if path not in groups:
                path.unlink()
                removed += 1
        self.dirty.clear()
        return {"written": written, "checked": checked, "removed": removed,
                "records": len(self.records)}
