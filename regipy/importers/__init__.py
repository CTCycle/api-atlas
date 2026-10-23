"""Import pipeline: fetch, parse, normalise, merge and persist.

Each importer returns fully normalised records and never writes to disk itself.
Store.upsert owns merging, which keeps a single implementation of the precedence
rules (curated beats imported, verification is never reset by an import).
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any, Callable

from .. import models, schema
from ..store import Store
from . import apis_guru, awesome_datasets, curated, fetch, public_apis

IMPORTERS: dict[str, dict[str, Any]] = {
    "public-apis": {
        "module": public_apis,
        "description": "public-apis/public-apis, MIT, free web APIs",
        "kind": "api",
        "fetchable": True,
    },
    "apis-guru": {
        "module": apis_guru,
        "description": "APIs.guru openapi-directory, CC0, OpenAPI specs",
        "kind": "api",
        "fetchable": True,
    },
    "awesome-datasets": {
        "module": awesome_datasets,
        "description": "awesomedata/awesome-public-datasets, MIT, topic datasets",
        "kind": "dataset",
        "fetchable": True,
    },
    "curated": {
        "module": curated,
        "description": "local curated seed entries, manual review",
        "kind": "mixed",
        "fetchable": False,
    },
}


def source_names() -> list[str]:
    return list(IMPORTERS)


def load_records(name: str, root: Path, source_dir: Path | None = None,
                 force_fetch: bool = False, version: str | None = None) -> list[dict[str, Any]]:
    """Parse one upstream source into normalised records."""
    if name not in IMPORTERS:
        raise SystemExit(f"unknown source '{name}', expected one of {', '.join(IMPORTERS)}")
    entry = IMPORTERS[name]
    module = entry["module"]
    upstream_dir = source_dir or (root / ".upstream")

    if name == "curated":
        records = module.parse_dir(root / "curation" / "seeds")
    else:
        record = fetch.fetch_source(name, upstream_dir, force=force_fetch)
        version = version or record.get("commit") or record.get("fetched_at")
        path = fetch.cached_file(name, upstream_dir)
        if name == "apis-guru":
            records = module.parse_file(path, version=version)
        else:
            records = module.parse_file(path)

    out: list[dict[str, Any]] = []
    for rec in records:
        rec = models.normalize_record(rec)
        models.apply_provider_policy(rec, str(root))
        if rec.get("category") == "unknown":
            inferred = schema.category_for_provider(
                (rec.get("provider") or {}).get("domain"), str(root))
            if inferred:
                rec["category"] = inferred
                rec["tags"] = sorted({*rec.get("tags", []), "category-inferred"})
        if name != "curated":
            rec["curation"] = {"level": "imported", "updated": models.TODAY}
        out.append(rec)
    return out


def import_source(name: str, store: Store, *, source_dir: Path | None = None,
                  force_fetch: bool = False, dry_run: bool = False) -> dict[str, Any]:
    records = load_records(name, store.root, source_dir=source_dir, force_fetch=force_fetch)
    counter: Counter = Counter()
    for rec in records:
        if dry_run:
            counter["parsed"] += 1
            continue
        counter[store.upsert(rec)] += 1
    return {"source": name, "parsed": len(records), "counts": dict(counter)}
