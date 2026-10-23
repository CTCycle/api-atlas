"""Command line interface: import, validate, search, export, verify, curate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import textwrap
from pathlib import Path
from typing import Any, Iterable

from . import __version__, importers, models, schema
from .store import Store

TODAY = dt.date.today().isoformat()


# --------------------------------------------------------------------- helpers
def _print_table(rows: Iterable[dict[str, Any]], columns: list[tuple[str, str]],
                 max_width: int = 46) -> None:
    data = [[str(row.get(key, ""))[:max_width] for key, _ in columns] for row in rows]
    headers = [label for _, label in columns]
    widths = [len(h) for h in headers]
    for line in data:
        for i, cell in enumerate(line):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for line in data:
        print(fmt.format(*line))


def _csv_arg(value: str | None) -> list[str] | None:
    if not value:
        return None
    return [part.strip() for part in value.split(",") if part.strip()]


def add_filter_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--category", help="category slug, comma separated")
    parser.add_argument("--kind", help="api or dataset")
    parser.add_argument("--pricing", help="free, freemium, paid, unknown")
    parser.add_argument("--access", help="public, api_key, oauth, registration, restricted, unknown")
    parser.add_argument("--commercial", help="allowed, restricted, prohibited, unknown")
    parser.add_argument("--status", help="active, deprecated, unavailable, unverified")
    parser.add_argument("--confidence", help="imported, partial, verified")
    parser.add_argument("--data-format", dest="data_format", help="json, csv, parquet, geojson, ...")
    parser.add_argument("--update-frequency", dest="update_frequency")
    parser.add_argument("--verified-since", dest="verified_since", help="YYYY-MM-DD")
    parser.add_argument("--provider", help="provider id or domain")
    parser.add_argument("--license", dest="license_spdx")
    parser.add_argument("--free-tier", dest="free_tier", action="store_true",
                        help="only entries with an indicated free tier")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--json", action="store_true", help="emit JSON")


def filters_from_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "category": _csv_arg(getattr(args, "category", None)),
        "kind": _csv_arg(getattr(args, "kind", None)),
        "pricing": _csv_arg(getattr(args, "pricing", None)),
        "access": _csv_arg(getattr(args, "access", None)),
        "commercial": _csv_arg(getattr(args, "commercial", None)),
        "status": _csv_arg(getattr(args, "status", None)),
        "confidence": _csv_arg(getattr(args, "confidence", None)),
        "data_format": _csv_arg(getattr(args, "data_format", None)),
        "update_frequency": _csv_arg(getattr(args, "update_frequency", None)),
        "verified_since": getattr(args, "verified_since", None),
        "provider": getattr(args, "provider", None),
        "license_spdx": _csv_arg(getattr(args, "license_spdx", None)),
        "free_tier": True if getattr(args, "free_tier", False) else None,
        "limit": getattr(args, "limit", None),
    }


def _load(root: Path) -> Store:
    return Store(root).load()


def _ensure_index(args: argparse.Namespace) -> None:
    """Build or refresh the SQLite index when the catalog is newer."""
    from . import search
    db = args.db
    catalog = args.root / "catalog"
    newest = 0.0
    for path in catalog.glob("*/*.jsonl"):
        newest = max(newest, path.stat().st_mtime)
    if not Path(db).exists() or Path(db).stat().st_mtime < newest:
        store = _load(args.root)
        search.build_index(store, db)


def _store_filter(records: list[dict[str, Any]], **filters: Any) -> list[dict[str, Any]]:
    """In-memory filtering used by commands that do not need the SQLite index."""
    def values(record: dict[str, Any], key: str) -> list[str]:
        value = schema.get_path(record, key)
        if isinstance(value, list):
            return [str(v).lower() for v in value]
        if value is None:
            return []
        return [str(value).lower()]

    def match(record: dict[str, Any], key: str, wanted: list[str] | None) -> bool:
        if not wanted:
            return True
        current = values(record, key)
        positives = [w for w in wanted if not w.startswith("!")]
        negatives = [w[1:] for w in wanted if w.startswith("!")]
        if any(n.lower() in current for n in negatives):
            return False
        if positives:
            return any(p.lower() in current for p in positives)
        return True

    out = []
    for rec in records:
        if not match(rec, "category", filters.get("category")):
            continue
        if not match(rec, "kind", filters.get("kind")):
            continue
        if not match(rec, "pricing.model", filters.get("pricing")):
            continue
        if not match(rec, "access.model", filters.get("access")):
            continue
        if not match(rec, "license.commercial_use", filters.get("commercial")):
            continue
        if not match(rec, "status", filters.get("status")):
            continue
        if not match(rec, "verification.confidence", filters.get("confidence")):
            continue
        if not match(rec, "update_frequency", filters.get("update_frequency")):
            continue
        if not match(rec, "formats", filters.get("data_format")):
            continue
        if not match(rec, "license.spdx", filters.get("license_spdx")):
            continue
        provider = filters.get("provider")
        if provider:
            prov = rec.get("provider") or {}
            if provider.lower() not in {str(prov.get("id", "")).lower(),
                                        str(prov.get("domain", "")).lower(),
                                        str(prov.get("name", "")).lower()}:
                continue
        since = filters.get("verified_since")
        if since:
            last = (rec.get("verification") or {}).get("last_verified") or ""
            if last < since:
                continue
        if filters.get("free_tier"):
            pricing = rec.get("pricing") or {}
            if not (pricing.get("free_tier_indicated") or pricing.get("model") in ("free", "freemium")):
                continue
        out.append(rec)
    limit = filters.get("limit")
    return out[:limit] if limit else out


def _short(value: Any, width: int = 40) -> str:
    text = "" if value is None else str(value)
    return text if len(text) <= width else text[: width - 1] + "…"


# -------------------------------------------------------------------- commands
def cmd_import(args: argparse.Namespace) -> int:
    store = _load(args.root)
    names = importers.source_names() if args.source in (None, "all") else [args.source]
    total = 0
    for name in names:
        result = importers.import_source(name, store, source_dir=args.source_dir,
                                         force_fetch=args.fetch, dry_run=args.dry_run)
        counts = ", ".join(f"{k}={v}" for k, v in sorted(result["counts"].items()))
        print(f"{name:<18} parsed={result['parsed']:<6} {counts}")
        total += result["parsed"]
    if args.dry_run:
        print(f"dry run, {total} records parsed, nothing written")
        return 0
    saved = store.save()
    print(f"saved: {saved['records']} records, {saved['written']} shards written, "
          f"{saved['removed']} shards removed")
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    from . import search
    store = _load(args.root)
    info = search.build_index(store, args.db)
    print(f"indexed {info['entries']} records into {info['path']}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    from . import search
    filters = filters_from_args(args)
    limit = filters.pop("limit") or 25
    _ensure_index(args)
    results = search.query(args.db, text=args.query, limit=limit, **filters)
    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
    rows = [{
        "id": r["id"],
        "name": _short(r.get("name"), 38),
        "category": r.get("category"),
        "pricing": (r.get("pricing") or {}).get("model"),
        "access": (r.get("access") or {}).get("model"),
        "confidence": (r.get("verification") or {}).get("confidence"),
        "status": r.get("status"),
    } for r in results]
    _print_table(rows, [("id", "ID"), ("name", "NAME"), ("category", "CATEGORY"),
                        ("pricing", "PRICING"), ("access", "ACCESS"),
                        ("confidence", "VERIFIED"), ("status", "STATUS")])
    print(f"\n{len(results)} result(s)")
    return 0


def cmd_show(args: argparse.Namespace) -> int:
    store = _load(args.root)
    rec = store.get(args.id) or store.find(args.id)
    if not rec:
        print(f"not found: {args.id}", file=sys.stderr)
        return 2
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    from . import export, search
    filters = filters_from_args(args)
    limit = filters.pop("limit")
    _ensure_index(args)
    records = search.query(args.db, text=args.query, limit=limit or 100000, **filters)
    text = export.export(records, fmt=args.format, out=args.out)
    if args.out:
        print(f"wrote {len(records)} records to {args.out}")
    else:
        print(text)
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = _load(args.root)
    stats = store.stats()
    if args.json:
        print(json.dumps(stats, indent=2, ensure_ascii=False))
        return 0
    print(f"records: {stats['total']}  providers: {stats['providers']}  "
          f"category coverage: {stats['coverage_ratio'] * 100:.0f}%")
    print(f"kinds: {stats['by_kind']}")
    print(f"confidence: {stats['by_confidence']}")
    print(f"status: {stats['by_status']}")
    print(f"pricing: {stats['by_pricing']}")
    print(f"access: {stats['by_access']}")
    print(f"commercial use: {stats['by_commercial_use']}")
    print("categories:")
    for category, count in stats["by_category"].items():
        print(f"  {category:<26} {count}")
    if stats["empty_categories"]:
        print(f"empty categories: {', '.join(stats['empty_categories'])}")
    if stats["flagged"]:
        print(f"flagged for review: {stats['flagged']}")
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    root = args.root
    store = _load(root)
    validator = schema.build_validator(str(root))
    errors: list[str] = []
    warnings: list[str] = []
    for rec in store.all():
        for problem in schema.validate_record(rec, validator, str(root)):
            errors.append(f"{rec.get('id')}: {problem}")
        if rec.get("flags"):
            warnings.append(f"{rec['id']}: flagged for review ({len(rec['flags'])})")
        prov = rec.get("provenance") or []
        if not prov or not all(p.get("source") for p in prov):
            errors.append(f"{rec.get('id')}: provenance entry without source")
    for path in sorted(store.catalog_dir.glob("*/*.jsonl")):
        kind_dir = path.parent.name
        if kind_dir not in ("apis", "datasets"):
            warnings.append(f"{path}: unexpected directory name")
        if path.stem not in schema.categories(root):
            warnings.append(f"{path}: category not in taxonomy")
    total = len(store.all())
    print(f"validated {total} records, {len(errors)} error(s), {len(warnings)} warning(s)")
    for line in errors[: args.max_errors]:
        print(f"  error: {line}")
    if len(errors) > args.max_errors:
        print(f"  ... {len(errors) - args.max_errors} more errors")
    if args.warnings:
        for line in warnings[: args.max_errors]:
            print(f"  warning: {line}")
    return 1 if errors or (args.strict and warnings) else 0


def cmd_linkcheck(args: argparse.Namespace) -> int:
    from . import linkcheck
    store = _load(args.root)
    result = linkcheck.linkcheck(
        store, limit=args.limit, kind=_csv_arg(args.kind),
        category=_csv_arg(args.category), workers=args.workers,
        timeout=args.timeout, dry_run=args.dry_run, force=args.force,
        max_age_days=args.max_age_days,
    )
    print(f"checked={result['checked']} ok={result['ok']} broken={result['broken']} "
          f"gated={result['gated']} errors={result['errors']} updated={result['updated']}")
    if not args.dry_run:
        saved = store.save()
        print(f"saved {saved['records']} records")
        report = args.root / "reports" / f"linkcheck-{TODAY}.json"
        report.parent.mkdir(parents=True, exist_ok=True)
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"report: {report}")
    return 0


def cmd_dedupe(args: argparse.Namespace) -> int:
    from . import dedupe
    store = _load(args.root)
    pairs = dedupe.find_duplicates(store, threshold=args.threshold,
                                   include_cross_provider=args.cross_provider)
    if args.json:
        print(json.dumps(pairs, indent=2, ensure_ascii=False))
    else:
        for pair in pairs[: args.limit]:
            print(f"{pair['score']:.2f}  {pair.get('confidence', 'review'):<6}  "
                  f"{pair['a']}  <=>  {pair['b']}  ({pair['reason']})")
        print(f"{len(pairs)} candidate pair(s), "
              f"{sum(1 for p in pairs if p.get('confidence') == 'high')} high confidence")
    if args.apply and pairs:
        summary = dedupe.apply_merges(store, pairs, force=args.force)
        saved = store.save()
        print(f"merged={summary['merged']} skipped={summary['skipped']} "
              f"shards_written={saved['written']}")
    return 0


def cmd_merge(args: argparse.Namespace) -> int:
    """Explicitly merge one entry into another after a manual review."""
    from . import dedupe
    store = _load(args.root)
    winner = store.get(args.winner) or store.find(args.winner)
    loser = store.get(args.loser) or store.find(args.loser)
    if not winner or not loser:
        print("both ids must resolve", file=sys.stderr)
        return 2
    if winner["id"] == loser["id"]:
        print("winner and loser are the same record", file=sys.stderr)
        return 2
    summary = dedupe.apply_merges(
        store,
        [{"a": winner["id"], "b": loser["id"], "score": 1.0,
          "reason": "manual_merge", "confidence": "high"}],
        force=True,
    )
    saved = store.save()
    print(f"merged={summary['merged']} skipped={summary['skipped']} "
          f"shards_written={saved['written']}")
    return 0


def cmd_alternatives(args: argparse.Namespace) -> int:
    store = _load(args.root)
    rec = store.get(args.id) or store.find(args.id)
    if not rec:
        print(f"not found: {args.id}", file=sys.stderr)
        return 2
    pricing_rank = {"free": 0, "freemium": 1, "unknown": 2, "paid": 3}
    tags = set(rec.get("tags") or [])
    wanted_pricing = _csv_arg(getattr(args, "pricing", None))
    wanted_access = _csv_arg(getattr(args, "access", None))
    wanted_commercial = _csv_arg(getattr(args, "commercial", None))
    candidates = []
    for other in store.all():
        if other["id"] == rec["id"]:
            continue
        if other.get("kind") != rec.get("kind"):
            continue
        if wanted_pricing and (other.get("pricing") or {}).get("model") not in wanted_pricing:
            continue
        if wanted_access and (other.get("access") or {}).get("model") not in wanted_access:
            continue
        if wanted_commercial and (other.get("license") or {}).get("commercial_use") not in wanted_commercial:
            continue
        shared = len(tags & set(other.get("tags") or []))
        if other.get("category") != rec.get("category") and shared == 0:
            continue
        score = shared * 2 + (3 if other.get("category") == rec.get("category") else 0)
        candidates.append((score, pricing_rank.get((other.get("pricing") or {}).get("model"), 2), other))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]["name"].lower()))
    rows = []
    for score, _, other in candidates[: args.limit]:
        rows.append({
            "id": other["id"],
            "name": _short(other.get("name"), 34),
            "category": other.get("category"),
            "pricing": (other.get("pricing") or {}).get("model"),
            "access": (other.get("access") or {}).get("model"),
            "commercial": (other.get("license") or {}).get("commercial_use"),
            "score": score,
        })
    print(f"alternatives for {rec['id']} ({rec.get('category')}, "
          f"{(rec.get('pricing') or {}).get('model')})")
    _print_table(rows, [("score", "SCORE"), ("id", "ID"), ("name", "NAME"),
                        ("pricing", "PRICING"), ("access", "ACCESS"),
                        ("commercial", "COMMERCIAL")])
    return 0


def cmd_flag(args: argparse.Namespace) -> int:
    store = _load(args.root)
    rec = store.get(args.id) or store.find(args.id)
    if not rec:
        print(f"not found: {args.id}", file=sys.stderr)
        return 2
    flags = rec.setdefault("flags", [])
    flags.append({"date": TODAY, "reason": args.reason, "reporter": args.reporter})
    if rec.get("status") == "active":
        rec["status"] = "unverified"
    rec.setdefault("verification", {})["notes"] = f"flagged {TODAY}: {args.reason}"
    store.save()
    print(f"flagged {rec['id']} ({len(flags)} flag(s))")
    return 0


def cmd_flags(args: argparse.Namespace) -> int:
    store = _load(args.root)
    flagged = [r for r in store.all() if r.get("flags")]
    rows = [{
        "id": r["id"],
        "date": r["flags"][-1].get("date"),
        "reason": _short(r["flags"][-1].get("reason"), 60),
        "status": r.get("status"),
    } for r in flagged]
    if args.json:
        print(json.dumps(flagged, indent=2, ensure_ascii=False))
        return 0
    _print_table(rows, [("id", "ID"), ("date", "FLAGGED"), ("reason", "REASON"),
                        ("status", "STATUS")], max_width=64)
    print(f"{len(flagged)} flagged record(s)")
    return 0


def cmd_categories(args: argparse.Namespace) -> int:
    store = _load(args.root)
    counts = store.stats()["by_category"]
    cats = schema.categories()
    if args.json:
        print(json.dumps({k: {"label": v["label"], "count": counts.get(k, 0)}
                          for k, v in cats.items()}, indent=2, ensure_ascii=False))
        return 0
    for slug, meta in cats.items():
        print(f"{slug:<26} {counts.get(slug, 0):>5}  {meta['label']}")
    return 0


def cmd_enrich(args: argparse.Namespace) -> int:
    """Re-apply provider policies and category inference to existing records."""
    store = _load(args.root)
    changed = 0
    for rec in store.all():
        before = json.dumps(rec, sort_keys=True)
        models.apply_provider_policy(rec, str(args.root))
        if rec.get("category") == "unknown":
            inferred = schema.category_for_provider(
                (rec.get("provider") or {}).get("domain"), str(args.root))
            if inferred:
                rec["category"] = inferred
                rec["tags"] = sorted({*rec.get("tags", []), "category-inferred"})
        if json.dumps(rec, sort_keys=True) != before:
            rec.setdefault("curation", {})["updated"] = TODAY
            changed += 1
    if args.dry_run:
        print(f"{changed} record(s) would change, nothing written")
        return 0
    saved = store.save()
    print(f"enriched {changed} record(s), {saved['written']} shard(s) written")
    return 0


def cmd_set(args: argparse.Namespace) -> int:
    store = _load(args.root)
    rec = store.get(args.id) or store.find(args.id)
    if not rec:
        print(f"not found: {args.id}", file=sys.stderr)
        return 2
    for assignment in args.assignments:
        if "=" not in assignment:
            print(f"expected field=value, got {assignment}", file=sys.stderr)
            return 2
        key, raw = assignment.split("=", 1)
        try:
            value = json.loads(raw)
        except json.JSONDecodeError:
            value = raw
        if value == "":
            value = None
        schema.set_path(rec, key.strip(), value)
    rec["curation"] = {"level": "curated", "updated": TODAY}
    rec["verification"]["method"] = "manual_review"
    if rec["verification"].get("confidence") == "imported":
        rec["verification"]["confidence"] = "partial"
    store.save()
    print(f"updated {rec['id']}")
    return 0


# ------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="regipy",
        description="Registry of APIs, public databases and downloadable datasets.",
    )
    parser.add_argument("--version", action="version", version=f"regipy {__version__}")
    parser.add_argument("--root", type=Path, default=None,
                        help="repository root (defaults to the nearest parent with schema/)")
    parser.add_argument("--db", type=Path, default=None, help="SQLite index path")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("import", help="import upstream catalogs and curated seeds")
    p.add_argument("source", nargs="?", default="all",
                   choices=[*importers.source_names(), "all"])
    p.add_argument("--source-dir", type=Path, default=None,
                   help="directory holding upstream snapshots (default .upstream/)")
    p.add_argument("--fetch", action="store_true", help="re-download upstream catalogs")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_import)

    p = sub.add_parser("build", help="rebuild the SQLite search index")
    p.set_defaults(func=cmd_build)

    p = sub.add_parser("search", help="search and filter entries")
    p.add_argument("query", nargs="?", default=None)
    add_filter_args(p)
    p.add_argument("--format", dest="data_format", help="alias for --data-format")
    p.set_defaults(func=cmd_search)

    p = sub.add_parser("show", help="show one record as JSON")
    p.add_argument("id")
    p.set_defaults(func=cmd_show)

    p = sub.add_parser("export", help="export filtered records")
    p.add_argument("query", nargs="?", default=None)
    p.add_argument("--format", default="csv", choices=["csv", "jsonl", "json", "md"])
    p.add_argument("--out", type=Path, default=None)
    add_filter_args(p)
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("stats", help="catalog statistics")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("validate", help="schema and invariant checks")
    p.add_argument("--strict", action="store_true", help="fail on warnings too")
    p.add_argument("--warnings", action="store_true", help="print warnings")
    p.add_argument("--max-errors", type=int, default=25)
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("linkcheck", help="verify website URLs and record dates")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--kind")
    p.add_argument("--category")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--max-age-days", type=int, default=30)
    p.add_argument("--force", action="store_true", help="ignore last_checked")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_linkcheck)

    p = sub.add_parser("dedupe", help="find or apply duplicate merges")
    p.add_argument("--threshold", type=float, default=0.82)
    p.add_argument("--cross-provider", action="store_true")
    p.add_argument("--apply", action="store_true")
    p.add_argument("--force", action="store_true",
                   help="apply merges even for low confidence pairs")
    p.add_argument("--json", action="store_true")
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_dedupe)

    p = sub.add_parser("merge", help="explicitly merge one entry into another")
    p.add_argument("winner")
    p.add_argument("loser")
    p.set_defaults(func=cmd_merge)

    p = sub.add_parser("alternatives", help="suggest alternatives to an entry")
    p.add_argument("id")
    p.add_argument("--pricing")
    p.add_argument("--access")
    p.add_argument("--commercial")
    p.add_argument("--limit", type=int, default=15)
    p.set_defaults(func=cmd_alternatives)

    p = sub.add_parser("flag", help="flag an entry as outdated or wrong")
    p.add_argument("id")
    p.add_argument("--reason", default="flagged for review")
    p.add_argument("--reporter", default=None)
    p.set_defaults(func=cmd_flag)

    p = sub.add_parser("flags", help="list flagged entries")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_flags)

    p = sub.add_parser("categories", help="list the taxonomy with counts")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_categories)

    p = sub.add_parser("set", help="edit fields on one record (marks it curated)")
    p.add_argument("id")
    p.add_argument("assignments", nargs="+", metavar="field=value")
    p.set_defaults(func=cmd_set)

    p = sub.add_parser("enrich", help="re-apply provider policies and category inference")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=cmd_enrich)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.root = (args.root or schema.repo_root()).resolve()
    if getattr(args, "db", None) is None:
        args.db = args.root / "data" / "registry.sqlite"
    else:
        args.db = Path(args.db).resolve()
    try:
        return args.func(args)
    except KeyboardInterrupt:
        print("interrupted", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
