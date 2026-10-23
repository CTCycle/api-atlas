"""Generate reports/coverage-report.md from the catalog.

Usage: python scripts/report.py [--out reports/coverage-report.md]
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from regipy import schema  # noqa: E402
from regipy.store import Store  # noqa: E402

TODAY = dt.date.today().isoformat()


def pct(part: int, total: int) -> str:
    return f"{100 * part / total:.1f}%" if total else "0.0%"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    out = args.out or (root / "reports" / "coverage-report.md")

    store = Store(root).load()
    records = store.all()
    total = len(records)
    stats = store.stats()
    cats = schema.categories(root)

    conf = Counter((r.get("verification") or {}).get("confidence") for r in records)
    status = Counter(r.get("status") for r in records)
    pricing = Counter((r.get("pricing") or {}).get("model", "unknown") for r in records)
    access = Counter((r.get("access") or {}).get("model", "unknown") for r in records)
    commercial = Counter((r.get("license") or {}).get("commercial_use", "unknown") for r in records)
    kinds = Counter(r.get("kind") for r in records)
    sources = Counter(p.get("source") for r in records for p in r.get("provenance") or [])
    multi_source = sum(1 for r in records if len(r.get("provenance") or []) > 1)
    known_license = sum(1 for r in records if (r.get("license") or {}).get("name"))
    known_pricing = sum(1 for r in records if (r.get("pricing") or {}).get("model") != "unknown")
    no_description = sum(1 for r in records if not r.get("description"))
    flagged = sum(1 for r in records if r.get("flags"))
    curated = sum(1 for r in records if (r.get("curation") or {}).get("level") == "curated")

    by_category: dict[str, list[dict]] = defaultdict(list)
    for rec in records:
        by_category[rec.get("category") or "unknown"].append(rec)

    lines: list[str] = []
    lines.append("# Catalog coverage report")
    lines.append("")
    lines.append(f"Generated {TODAY} by `python scripts/report.py` from the JSONL shards.")
    lines.append("")
    lines.append("## Size")
    lines.append("")
    lines.append(f"- Records: {total}")
    lines.append(f"- APIs: {kinds.get('api', 0)}, datasets: {kinds.get('dataset', 0)}")
    lines.append(f"- Distinct provider identities: {stats['providers']}")
    lines.append(f"- Records merged from more than one source: {multi_source}")
    lines.append(f"- Curated records (manual review): {curated}")
    lines.append(f"- Categories populated: {len(cats) - len(stats['empty_categories'])} of {len(cats)} "
                 f"({stats['coverage_ratio'] * 100:.0f}%)")
    lines.append("")
    lines.append("### Records per upstream source")
    lines.append("")
    lines.append("| Source | Records |")
    lines.append("|---|---:|")
    for source, count in sources.most_common():
        lines.append(f"| {source or 'unknown'} | {count} |")
    lines.append("")
    lines.append("A record can appear under several sources, so these numbers sum to more than the total.")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append("| Tier | Records | Share |")
    lines.append("|---|---:|---:|")
    for tier in ("verified", "partial", "imported"):
        lines.append(f"| {tier} | {conf.get(tier, 0)} | {pct(conf.get(tier, 0), total)} |")
    lines.append("")
    lines.append("Status: " + ", ".join(f"{key} {value}" for key, value in status.most_common()))
    lines.append("")
    lines.append("## Access and pricing")
    lines.append("")
    lines.append("| Field | Value | Records | Share |")
    lines.append("|---|---|---:|---:|")
    for key, value in access.most_common():
        lines.append(f"| access.model | {key} | {value} | {pct(value, total)} |")
    for key, value in pricing.most_common():
        lines.append(f"| pricing.model | {key} | {value} | {pct(value, total)} |")
    for key, value in commercial.most_common():
        lines.append(f"| license.commercial_use | {key} | {value} | {pct(value, total)} |")
    lines.append("")
    lines.append(f"Records with a named licence: {known_license} ({pct(known_license, total)}). "
                 f"Records with a known pricing model: {known_pricing} ({pct(known_pricing, total)}).")
    lines.append("")
    lines.append("## Category coverage")
    lines.append("")
    lines.append("| Category | Records | APIs | Datasets | Named licence | Verified |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for slug, meta in cats.items():
        group = by_category.get(slug, [])
        if not group:
            continue
        lines.append(
            f"| {slug} | {len(group)} "
            f"| {sum(1 for r in group if r.get('kind') == 'api')} "
            f"| {sum(1 for r in group if r.get('kind') == 'dataset')} "
            f"| {sum(1 for r in group if (r.get('license') or {}).get('name'))} "
            f"| {sum(1 for r in group if (r.get('verification') or {}).get('confidence') == 'verified')} |"
        )
    lines.append("")
    if stats["empty_categories"]:
        lines.append("Empty categories: " + ", ".join(stats["empty_categories"]) + ".")
        lines.append("")
    lines.append("## Gaps")
    lines.append("")
    lines.append(f"- Records without a description: {no_description} ({pct(no_description, total)}).")
    lines.append(f"- Records with unknown pricing: {total - known_pricing} ({pct(total - known_pricing, total)}).")
    lines.append(f"- Records with unknown commercial use: {commercial.get('unknown', 0)} "
                 f"({pct(commercial.get('unknown', 0), total)}).")
    lines.append(f"- Records flagged for review: {flagged}.")
    lines.append("")
    lines.append("Pricing and licensing are the least complete fields because two of the three upstream")
    lines.append("catalogs do not record them at all. Licensed coverage improves through curated seeds and")
    lines.append("provider policies, not through inference.")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append("- Imported records carry the upstream description. They are not independently confirmed.")
    lines.append("- An HTTP 200 proves a URL answers, not that the API works, the quota holds or the")
    lines.append("  licence statement is current.")
    lines.append("- Free tier limits are only present where a curated entry quotes the provider page;")
    lines.append("  absence means unknown, not unlimited.")
    lines.append("- Coverage is uneven across categories because it mirrors the upstream catalogs.")
    lines.append("- Categories with fewer than ten records should be treated as thin.")
    lines.append("")
    lines.append("## Refresh procedure")
    lines.append("")
    lines.append("1. `python -m regipy.cli import all` re-imports all three upstream catalogs and the seeds.")
    lines.append("2. `python -m regipy.cli enrich` re-applies provider policies and category inference.")
    lines.append("3. `python -m regipy.cli linkcheck --max-age-days 30` re-verifies URLs and dates.")
    lines.append("4. `python -m regipy.cli dedupe` reviews candidates; `merge` applies a reviewed pair.")
    lines.append("5. `python -m regipy.cli build` rebuilds the index, `validate` gates the result.")
    lines.append("6. `python scripts/report.py` regenerates this file.")
    lines.append("")
    lines.append("## Future improvements")
    lines.append("")
    lines.append("- Enrich the imported long tail with per provider quotas, formats and coverage.")
    lines.append("- Add more institutional and paid sources, where the catalog is thinnest.")
    lines.append("- Snapshot upstream catalog versions in provenance so a refresh is diffable.")
    lines.append("- Grow the verification sample beyond URL reachability into documented capability checks.")
    lines.append("")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out} ({len(lines)} lines, {total} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
