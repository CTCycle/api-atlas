#!/usr/bin/env python3
"""Discover live OpenAPI/Swagger specifications for catalogued APIs.

A homepage that answers 200 proves a website exists. It does not prove the API
works. This script looks for the machine-readable contract instead: it reads the
website and the docs page, collects candidate specification links (and tries the
conventional paths), then validates that the response really is an OpenAPI or
Swagger document with a non-empty `paths` object.

That is the strongest evidence a directory can offer without an API key: the
provider is publishing a contract that parses.

Usage:
    python scripts/probe.py                       # every API entry
    python scripts/probe.py --category finance
    python scripts/probe.py --limit 50 --workers 8
    python scripts/probe.py --out reports/probe.json

Output: reports/probe-YYYY-MM-DD.json with one record per entry and a summary.
Nothing is written to catalog/; a human decides whether to cite a spec.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import catalog  # noqa: E402  (stdlib-only helper module in this repo)

REPORT_DIR = ROOT / "reports"

SPEC_HREF = re.compile(
    r"""["'(]([^"'()\s]*(?:openapi|swagger|api-docs|apispec)[^"'()\s]*\.(?:json|yaml|yml))["')]""",
    re.I,
)
CONVENTIONAL = (
    "/openapi.json", "/swagger.json", "/openapi.yaml", "/swagger/v1/swagger.json",
    "/v2/api-docs", "/v3/api-docs", "/api-docs", "/api/openapi.json",
    "/.well-known/openapi.json",
)
MAX_SPEC_BYTES = 512 * 1024
MAX_REDIRECTS = 5
REDIRECT_STATUSES = {301, 302, 303, 307, 308}
SPEC_SUFFIXES = (".json", ".yaml", ".yml")


def _fetch_following(url: str, timeout: float = 20.0,
                     read_body: int = MAX_SPEC_BYTES) -> tuple[int | None, bytes, str, str | None]:
    """GET a URL, following redirects. Returns (status, body, final_url, error).

    catalog._fetch deliberately refuses redirects so the link check can report the
    hop. Here the destination is what matters, so follow it (bounded) and resolve
    relative Location headers against the URL that answered.
    """
    current = url
    status: int | None = None
    body = b""
    error: str | None = None
    for _ in range(MAX_REDIRECTS + 1):
        status, headers, body, error = catalog._fetch(current, "GET", timeout,
                                                      read_body=read_body)
        if status is None or error:
            return status, body, current, error
        location = (headers or {}).get("location")
        if status in REDIRECT_STATUSES and location:
            current = urljoin(current, location)
            continue
        return status, body, current, None
    return status, body, current, f"too many redirects (>{MAX_REDIRECTS})"


def parse_document(body: bytes) -> dict | None:
    """Parse a JSON or YAML body into a mapping, or return None.

    YAML support is optional: PyYAML when importable, otherwise YAML candidates
    are skipped rather than misread (the probe stays stdlib-only by default).
    """
    if not body:
        return None
    text = body.decode("utf-8", "replace").lstrip("\ufeff \t\r\n")
    if not text:
        return None
    if text[0] in "{[":
        try:
            doc = json.loads(text)
        except ValueError:
            doc = None
        if isinstance(doc, dict):
            return doc
    try:
        import yaml  # optional dependency
    except ImportError:
        return None
    try:
        doc = yaml.safe_load(text)
    except Exception:  # noqa: BLE001 - malformed YAML is a non-result, not a crash
        return None
    return doc if isinstance(doc, dict) else None


def spec_metadata(url: str, body: bytes) -> dict | None:
    """Return spec metadata if the body is an OpenAPI/Swagger document with paths."""
    doc = parse_document(body)
    if not doc:
        return None
    if "openapi" not in doc and "swagger" not in doc:
        return None
    paths = doc.get("paths")
    if not isinstance(paths, dict) or not paths:
        return None
    info = doc.get("info") if isinstance(doc.get("info"), dict) else {}
    meta = {
        "spec_url": url,
        "spec_version": doc.get("openapi") or doc.get("swagger"),
        "spec_title": (info.get("title") or "")[:120] or None,
        "path_count": len(paths),
    }
    if len(body) >= MAX_SPEC_BYTES:
        # the read is capped: the document is real, its path count is a floor
        meta["truncated"] = True
    return meta


def _looks_like_spec(url: str) -> bool:
    """A docs URL that already is a specification file, not a page describing one."""
    path = urlsplit(url).path.casefold()
    name = path.rsplit("/", 1)[-1]
    return name.endswith(SPEC_SUFFIXES) and any(
        token in name for token in ("openapi", "swagger", "api-docs", "apispec"))


def candidate_spec_urls(entry) -> list[str]:
    """Spec links found on the website and docs pages, then conventional paths.

    A docs URL that is itself a specification document is a candidate too: 83 rows
    point straight at /openapi.json or /swagger.json and would otherwise be probed
    only at guessed paths.
    """
    found: list[str] = []
    for page in (entry.url, entry.docs):
        if not page:
            continue
        status, body, final_url, _ = _fetch_following(page)
        if _looks_like_spec(final_url) or _looks_like_spec(page):
            found.append(final_url)
        if not body or status is None or not 200 <= status < 300:
            # an error page's links are about the error, not the API
            continue
        text = body.decode("utf-8", "replace")
        for match in SPEC_HREF.findall(text):
            found.append(urljoin(final_url, match))
    origin = "{0.scheme}://{0.netloc}".format(urlsplit(entry.url))
    found.extend(origin + path for path in CONVENTIONAL)
    seen: set[str] = set()
    unique = []
    for url in found:
        key = url.rstrip("/")
        if key not in seen:
            seen.add(key)
            unique.append(url)
    return unique[:12]


def validate_spec(url: str) -> dict | None:
    """Return spec metadata if the URL serves a parseable OpenAPI/Swagger document."""
    status, body, final_url, error = _fetch_following(url, timeout=25)
    if error or not body or status is None or not 200 <= status < 300:
        return None
    return spec_metadata(final_url, body)


def probe(entry) -> dict:
    record = {"name": entry.name, "category": entry.category, "type": entry.type,
              "website": entry.url, "spec": None, "tried": 0, "error": None}
    try:
        candidates = candidate_spec_urls(entry)
        record["tried"] = len(candidates)
        for url in candidates:
            spec = validate_spec(url)
            if spec:
                record["spec"] = spec
                break
    except Exception as exc:  # noqa: BLE001
        record["error"] = f"{type(exc).__name__}: {exc}"
    return record


def write_index(path: str) -> int:
    """Merge every probe report into one index, ignoring rows no longer catalogued."""
    entries = catalog.load(catalog.Problems(), strict=False)
    current = {(e.category, e.name) for e in entries}
    merged: dict[tuple[str, str], dict] = {}
    probed: set[tuple[str, str]] = set()
    for report in sorted(REPORT_DIR.glob("probe-*.json")):
        if report.name.startswith("probe-smoke"):
            continue
        for record in json.loads(report.read_text(encoding="utf-8"))["records"]:
            key = (record["category"], record["name"])
            if key not in current:
                continue
            probed.add(key)
            if record.get("spec"):
                merged[key] = {
                    "name": record["name"],
                    "category": record["category"],
                    "type": record["type"],
                    "website": record["website"],
                    **record["spec"],
                }
    rows = sorted(merged.values(), key=lambda r: (r["category"], r["name"].casefold()))
    Path(path).write_text(json.dumps({
        "generated": dt.date.today().isoformat(),
        "description": "Entries that publish a parseable OpenAPI or Swagger document, "
                       "discovered by scripts/probe.py. Absence is not proof that an API "
                       "has no spec: it may sit behind auth or on another host.",
        "entries_probed": len(probed),
        "specs": len(rows),
        "entries": rows,
    }, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({len(rows)} of {len(probed)} probed entries publish a spec)")
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="random sample size (0 = all)")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--category")
    ap.add_argument("--type", default="API", choices=sorted(catalog.TYPES),
                    help="entry type to probe (default API; use '' for all)")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--missing", action="store_true",
                    help="only probe entries that no earlier probe report has seen, so a "
                         "second run after a catalog expansion costs minutes, not hours")
    ap.add_argument("--out")
    ap.add_argument("--index", metavar="PATH",
                    help="also write an index of every discovered spec, merged from "
                         "all probe reports (e.g. data/openapi-index.json)")
    ap.add_argument("--index-only", action="store_true",
                    help="rebuild --index from the existing reports and exit, without "
                         "probing anything")
    args = ap.parse_args(argv)

    if args.index_only:
        if not args.index:
            ap.error("--index-only needs --index PATH")
        write_index(args.index)
        return 0

    entries = catalog.load(catalog.Problems(), strict=False)
    if args.type:
        entries = [e for e in entries if e.type == args.type]
    if args.category:
        entries = [e for e in entries if e.category == args.category]
    if args.missing:
        known = set()
        for report in sorted(REPORT_DIR.glob("probe-*.json")):
            if report.name.startswith("probe-smoke"):
                continue
            for record in json.loads(report.read_text(encoding="utf-8"))["records"]:
                known.add((record["category"], record["name"]))
        before = len(entries)
        entries = [e for e in entries if (e.category, e.name) not in known]
        print(f"skipping {before - len(entries)} entries that a previous run already probed")
    if args.limit:
        import random
        random.Random(args.seed).shuffle(entries)
        entries = entries[: args.limit]

    print(f"probing {len(entries)} entries (workers={args.workers})", flush=True)
    records: list[dict] = []
    done = 0
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for record in pool.map(probe, entries):
            records.append(record)
            done += 1
            if done % 50 == 0:
                print(f"  {done}/{len(entries)}  specs found: "
                      f"{sum(1 for r in records if r['spec'])}", flush=True)

    found = [r for r in records if r["spec"]]
    records.sort(key=lambda r: (r["category"], r["name"].casefold()))
    if args.out:
        out = Path(args.out).resolve()
    else:
        # never clobber an earlier run: a second sweep on the same day would
        # otherwise destroy the evidence the first one collected
        base = REPORT_DIR / f"probe-{dt.date.today().isoformat()}"
        out, n = base.with_suffix(".json"), 1
        while out.exists():
            n += 1
            out = REPORT_DIR / f"{base.name}-{n}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "entries_probed": len(records),
        "specs_found": len(found),
        "by_category": dict(Counter(r["category"] for r in found).most_common()),
        "records": records,
    }, indent=1), encoding="utf-8")

    if args.index:
        write_index(args.index)

    print(f"\n{len(found)} of {len(records)} entries publish a valid OpenAPI/Swagger document")
    try:
        print(f"wrote {out.relative_to(ROOT)}")
    except ValueError:
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
