#!/usr/bin/env python3
"""API Atlas catalog tool.

The catalog is Markdown: one file per category under catalog/, each holding a
single table. Those files are the source of truth. This script is optional and
stdlib-only. It validates the tables, exports machine-readable copies, checks
links and writes maintenance reports.

It never edits the catalog. Report output is a proposal for a human to apply.

Usage:
    python scripts/catalog.py validate
    python scripts/catalog.py stats
    python scripts/catalog.py export --format jsonl
    python scripts/catalog.py linkcheck --limit 200
    python scripts/catalog.py report
    python scripts/catalog.py duplicates
    python scripts/catalog.py stale --days 180
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import csv
import datetime as dt
import json
import random
import re
import ssl
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin, urlsplit

ROOT = Path(__file__).resolve().parent.parent
CATALOG_DIR = ROOT / "catalog"
REPORT_DIR = ROOT / "reports"
DATA_DIR = ROOT / "data"

USER_AGENT = (
    "api-atlas-linkcheck/2.0 (+https://github.com/CTCycle/api-atlas; "
    "catalog link validation)"
)

# (slug, title, blurb) in README order
CATEGORIES = [
    ("agriculture", "Agriculture", "Crops, soils, farm economics, yields and agri-food statistics."),
    ("ai-ml", "AI & Machine Learning", "Model inference, embeddings, speech, vision, training data and ML platforms."),
    ("animals", "Animals", "Species data, pet and wildlife records, animal images and shelters."),
    ("art-design", "Art & Design", "Museums, image collections, design assets, colour and typography data."),
    ("blockchain-crypto", "Blockchain & Cryptocurrency", "Chain data, market prices, wallets, explorers and smart contract tooling."),
    ("business-commerce", "Business & Commerce", "Company data, CRMs, invoicing, product catalogs and marketplaces."),
    ("cloud-infrastructure", "Cloud & Infrastructure", "Hosting, storage, container and deployment platforms."),
    ("communication", "Communication", "Email, SMS, voice, chat and notification services."),
    ("data-analytics", "Data & Analytics", "Analytics platforms, event pipelines, BI and metrics services."),
    ("developer-tools", "Developer Tools", "Version control, CI, code quality, package registries and build tooling."),
    ("documents-productivity", "Documents & Productivity", "Document conversion, file storage, notes, tasks and office automation."),
    ("economics", "Economics", "Macroeconomic indicators, trade, labour and price statistics."),
    ("education", "Education", "Schools, universities, courses, learning content and academic records."),
    ("energy", "Energy", "Electricity grids, fuel prices, renewables and emissions data."),
    ("entertainment-media", "Entertainment & Media", "Film, television, music, books, podcasts and media metadata."),
    ("finance", "Finance", "Banking, markets, payments data, forex and financial statements."),
    ("food-nutrition", "Food & Nutrition", "Food composition, recipes, restaurants and product nutrition data."),
    ("games", "Games", "Game databases, player stats, assets and community APIs."),
    ("geospatial", "Geospatial", "Maps, geocoding, satellite imagery, elevation and boundary data."),
    ("government", "Government & Public Sector", "Legislation, procurement, civic records and public sector APIs."),
    ("health-medical", "Health & Medical", "Clinical trials, medical literature, health statistics and terminology."),
    ("housing-real-estate", "Housing & Real Estate", "Property listings, prices, rents, permits and housing statistics."),
    ("humanitarian-development", "Humanitarian & Development", "Aid flows, displacement, conflict events and development indicators."),
    ("identity-security", "Identity & Security", "Authentication, breach data, vulnerability feeds and threat intelligence."),
    ("iot", "IoT & Devices", "Device clouds, sensor networks and hardware telemetry."),
    ("jobs-hr", "Jobs & HR", "Job boards, salary data, recruiting and workforce datasets."),
    ("legal", "Legal", "Case law, statutes, court records and legal reference data."),
    ("life-sciences", "Life Sciences", "Genomics, proteins, chemistry, pharmacology and biomedical datasets."),
    ("logistics-transportation", "Transportation & Logistics", "Transit, shipping, flights, routing and vehicle data."),
    ("manufacturing", "Manufacturing & Industry", "Industrial standards, materials, supply chains and factory data."),
    ("marketing-social", "Marketing & Social", "Social platforms, advertising, audience and influencer data."),
    ("mathematics", "Mathematics", "Mathematical sequences, proofs, symbolic computation and statistics."),
    ("mcp-servers", "MCP Servers", "Model Context Protocol servers that expose tools and data to AI agents."),
    ("news-journalism", "News & Journalism", "News archives, headlines, fact checking and media monitoring."),
    ("open-data", "Open Data Portals", "National and international open data catalogs and CKAN portals."),
    ("patent-ip", "Patents & IP", "Patent offices, trademarks and intellectual property records."),
    ("payments", "Payments", "Payment processing, banking rails, tax and billing services."),
    ("science-research", "Science & Research", "Publications, citations, physics, chemistry and earth observation."),
    ("search", "Search", "Web, academic and specialist search engines."),
    ("space", "Space & Astronomy", "Satellite tracking, astronomy archives, launches and orbital data."),
    ("sports-fitness", "Sports & Fitness", "Scores, statistics, fitness tracking and sports data."),
    ("telecommunications", "Telecommunications", "Phone numbers, carriers, number portability and messaging data."),
    ("test-data", "Test Data", "Fake users, addresses, images and generators for testing."),
    ("travel", "Travel", "Flights, hotels, places, transit and trip planning."),
    ("weather-climate", "Weather & Climate", "Forecasts, observations, reanalysis and climate projections."),
]
CATEGORY_SLUGS = {c[0] for c in CATEGORIES}
CATEGORY_TITLES = {c[0]: c[1] for c in CATEGORIES}

TYPES = {"API", "Dataset", "Portal", "MCP"}
ACCESS = {"Free", "Free tier", "Freemium", "Paid", "Restricted", "-"}
AUTH = {"None", "API key", "OAuth", "Registration", "Account", "-"}
SOURCES = {"editorial", "public-apis", "APIs.guru", "awesome-datasets"}

HEADER = "| Name | Type | Description | Access | Auth | License | Docs | Source | Checked |"
DIVIDER = "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"

LINK = re.compile(r"^\[(.+)\]\((https?://[^)\s]+)\)$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


# ---------------------------------------------------------------- model


@dataclass
class Entry:
    name: str
    url: str
    type: str
    description: str
    access: str
    auth: str
    license: str
    docs: str
    source: str
    checked: str
    category: str
    line: int = 0

    @property
    def slug(self) -> str:
        host = urlsplit(self.url).netloc.lower().removeprefix("www.")
        name = re.sub(r"[^a-z0-9]+", "-", self.name.lower()).strip("-")
        return f"{host}/{name}"


@dataclass
class Problems:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def error(self, where: str, msg: str) -> None:
        self.errors.append(f"{where}: {msg}")

    def warn(self, where: str, msg: str) -> None:
        self.warnings.append(f"{where}: {msg}")


def table_files() -> list[Path]:
    return sorted(p for p in CATALOG_DIR.glob("*.md") if p.name != "README.md")


def parse_cell(cell: str) -> str:
    return cell.strip()


def parse_file(path: Path, problems: Problems) -> list[Entry]:
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or not lines[0].startswith("# "):
        problems.error(rel, "file must start with an H1 title")
    if HEADER not in lines:
        problems.error(rel, f"missing table header: {HEADER}")
        return []
    start = lines.index(HEADER)
    if start + 1 >= len(lines) or lines[start + 1].strip() != DIVIDER:
        problems.error(rel, "header must be followed by the divider row")
        return []

    entries: list[Entry] = []
    for offset, raw in enumerate(lines[start + 2:], start=start + 3):
        line = raw.strip()
        if not line:
            break
        if not line.startswith("|"):
            problems.error(f"{rel}:{offset}", "table row must start with '|'")
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 9:
            problems.error(f"{rel}:{offset}", f"expected 9 columns, found {len(cells)}")
            continue

        name_cell, type_, desc, access, auth, lic, docs, source, checked = cells
        m = LINK.match(name_cell)
        if not m:
            problems.error(f"{rel}:{offset}", f"name cell must be a link, got {name_cell!r}")
            continue
        name, url = m.group(1).strip(), m.group(2).strip()

        if type_ not in TYPES:
            problems.error(f"{rel}:{offset}", f"unknown type {type_!r}")
        if access not in ACCESS:
            problems.error(f"{rel}:{offset}", f"unknown access {access!r}")
        if auth not in AUTH:
            problems.error(f"{rel}:{offset}", f"unknown auth {auth!r}")
        for part in source.split(","):
            if part.strip() and part.strip() not in SOURCES:
                problems.error(f"{rel}:{offset}", f"unknown source {part.strip()!r}")
        if checked != "-" and not DATE.match(checked):
            problems.error(f"{rel}:{offset}", f"checked must be an ISO date or '-', got {checked!r}")
        if docs != "-":
            dm = LINK.match(docs)
            if not dm:
                problems.error(f"{rel}:{offset}", f"docs cell must be a link or '-', got {docs!r}")
            else:
                docs = dm.group(2).strip()
        else:
            docs = ""
        if not 10 <= len(desc) <= 240:
            problems.warn(f"{rel}:{offset}", f"description length {len(desc)} outside 10-240")
        if desc.endswith(".") and not desc.endswith("..."):
            problems.warn(f"{rel}:{offset}", "description ends with a period")
        if name != name.strip() or "  " in name:
            problems.warn(f"{rel}:{offset}", "name has irregular spacing")

        entries.append(Entry(name=name, url=url, type=type_, description=desc,
                             access=access, auth=auth, license=lic, docs=docs,
                             source=source, checked=checked,
                             category=path.stem, line=offset))

    if not entries:
        problems.warn(rel, "no entries")

    # alphabetical order
    keys = [e.name.casefold() for e in entries]
    if keys != sorted(keys):
        for i in range(1, len(keys)):
            if keys[i] < keys[i - 1]:
                problems.error(f"{rel}", f"rows not alphabetical: {entries[i].name!r} after {entries[i-1].name!r}")
                break

    # duplicates inside the file
    seen: dict[str, Entry] = {}
    norm = lambda s: re.sub(r"[^a-z0-9]", "", s.casefold())
    for e in entries:
        k = norm(e.name)
        if k in seen:
            problems.error(f"{rel}:{e.line}", f"duplicate name {e.name!r} (first at line {seen[k].line})")
        seen[k] = e
    return entries


def load(problems: Problems | None = None, strict: bool = True) -> list[Entry]:
    problems = problems if problems is not None else Problems()
    entries: list[Entry] = []
    files = table_files()
    if strict:
        present = {p.stem for p in files}
        for slug in sorted(CATEGORY_SLUGS - present):
            problems.error("catalog", f"missing category file catalog/{slug}.md")
        for slug in sorted(present - CATEGORY_SLUGS):
            problems.error("catalog", f"unknown category file catalog/{slug}.md (add it to CATEGORIES in scripts/catalog.py)")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for slug in sorted(present):
            if f"catalog/{slug}.md" not in readme:
                problems.error("README.md", f"no navigation link to catalog/{slug}.md")
    for p in files:
        entries.extend(parse_file(p, problems))
    return entries


# ---------------------------------------------------------------- commands


def cmd_validate(args: argparse.Namespace) -> int:
    problems = Problems()
    entries = load(problems, strict=True)

    by_url: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        by_url[e.url.rstrip("/")].append(e)
    for url, group in by_url.items():
        if len(group) > 1:
            names = ", ".join(f"{g.name} ({g.category})" for g in group)
            problems.warn("catalog", f"same URL listed {len(group)} times: {url} -> {names}")

    # the committed export must agree with the tables, field for field
    export = DATA_DIR / "catalog.jsonl"
    if export.exists():
        rows = []
        for number, line in enumerate(export.read_text(encoding="utf-8").splitlines(), 1):
            try:
                rows.append(json.loads(line))
            except ValueError as exc:
                problems.error(f"data/catalog.jsonl:{number}", f"not valid JSON: {exc}")
        expected = {e.slug for e in entries}
        seen = {r.get("id") for r in rows}
        for missing in sorted(expected - seen)[:10]:
            problems.error("data/catalog.jsonl", f"missing row {missing} (run: export --format jsonl)")
        for extra in sorted(seen - expected)[:10]:
            problems.error("data/catalog.jsonl", f"row {extra} is not in the tables (stale export)")
        for r in rows:
            if r.get("type") not in TYPES:
                problems.error(f"data/catalog.jsonl {r.get('id')}", f"bad type {r.get('type')!r}")
            if r.get("access") not in ACCESS:
                problems.error(f"data/catalog.jsonl {r.get('id')}", f"bad access {r.get('access')!r}")
            if r.get("auth") not in AUTH:
                problems.error(f"data/catalog.jsonl {r.get('id')}", f"bad auth {r.get('auth')!r}")
            if r.get("checked") is not None and not DATE.match(str(r["checked"])):
                problems.error(f"data/catalog.jsonl {r.get('id')}", "bad checked date")

    for line in problems.errors:
        print("ERROR  ", line)
    for line in problems.warnings:
        print("WARN   ", line)
    print(f"\n{len(entries)} entries in {len(table_files())} files, "
          f"{len(problems.errors)} errors, {len(problems.warnings)} warnings")
    return 1 if problems.errors else 0


def cmd_stats(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    print(f"{len(entries)} entries\n")
    print("by category")
    for cat, n in Counter(e.category for e in entries).most_common():
        print(f"  {cat:26s} {n:4d}")
    print("\nby type   ", dict(Counter(e.type for e in entries)))
    print("by access ", dict(Counter(e.access for e in entries).most_common()))
    print("by auth   ", dict(Counter(e.auth for e in entries).most_common()))
    print("by source ", dict(Counter(e.source for e in entries).most_common()))
    checked = Counter("never" if e.checked == "-" else "dated" for e in entries)
    print("checked   ", dict(checked))
    if args.json:
        print(json.dumps([asdict(e) for e in entries], indent=1)[:0])
    return 0


def _row(e: Entry) -> dict:
    """The machine-readable record, including derived fields agents can filter on.

    Derived fields are deliberately date-independent: the committed export must not
    change just because a day passed, or the CI freshness check would fail on every
    unrelated pull request.
    """
    checked = None if e.checked == "-" else e.checked
    return {
        "id": e.slug,
        "name": e.name,
        "type": e.type,
        "category": e.category,
        "description": e.description,
        "website": e.url,
        "docs": e.docs or None,
        "access": e.access,
        "auth": e.auth,
        "license": e.license,
        "source": e.source,
        "checked": checked,
        # derived, never hand-edited
        "verified": checked is not None,
        "docs_present": bool(e.docs),
        "license_known": e.license not in {"-", ""},
    }


def cmd_export(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    DATA_DIR.mkdir(exist_ok=True)
    if args.format == "jsonl":
        out = Path(args.out) if args.out else DATA_DIR / "catalog.jsonl"
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            for e in entries:
                fh.write(json.dumps(_row(e), sort_keys=True, ensure_ascii=False) + "\n")
    elif args.format == "json":
        out = Path(args.out) if args.out else DATA_DIR / "catalog.json"
        # one object per line: a JSON array that still produces line-sized diffs
        rows = [json.dumps(_row(e), sort_keys=True, ensure_ascii=False) for e in entries]
        out.write_text("[\n" + ",\n".join(rows) + "\n]\n", encoding="utf-8")
    else:
        out = Path(args.out) if args.out else DATA_DIR / "catalog.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh, lineterminator="\n")
            w.writerow(["id", "name", "type", "category", "description", "website",
                        "docs", "access", "auth", "license", "source", "checked",
                        "verified", "docs_present", "license_known"])
            for e in entries:
                r = _row(e)
                w.writerow([r["id"], r["name"], r["type"], r["category"], r["description"],
                            r["website"], r["docs"] or "", r["access"], r["auth"],
                            r["license"], r["source"], r["checked"] or "",
                            r["verified"], r["docs_present"], r["license_known"]])
    print(f"wrote {out} ({len(entries)} entries)")
    return 0


def cmd_shortlist(args: argparse.Namespace) -> int:
    """Generate docs/no-auth.md: the free, keyless subset, grouped by category."""
    entries = load(Problems(), strict=False)
    wanted = [e for e in entries
              if e.auth == "None" and e.access in {"Free", "Free tier"}]
    by_cat: dict[str, list[Entry]] = defaultdict(list)
    for e in wanted:
        by_cat[e.category].append(e)

    lines = [
        "# No key needed",
        "",
        f"{len(wanted)} catalogued resources that need no credentials: `Auth` is `None`",
        "and the cheapest usable tier is `Free` or `Free tier`. Nothing here requires an",
        "account, a key or an approval.",
        "",
        "Generated from the catalog by `python scripts/catalog.py shortlist`. Edit the",
        "category tables, not this file.",
        "",
    ]
    for slug, title, _ in CATEGORIES:
        rows = sorted(by_cat.get(slug, []), key=lambda e: e.name.casefold())
        if not rows:
            continue
        lines += [f"## {title} ({len(rows)})", ""]
        for e in rows:
            same = e.docs and e.docs.rstrip("/") == e.url.rstrip("/")
            docs = f" ([docs]({e.docs}))" if e.docs and not same else ""
            lines.append(f"- [{e.name}]({e.url}){docs} - {e.description}")
        lines.append("")
    out = ROOT / "docs" / "no-auth.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)} ({len(wanted)} entries in {len(by_cat)} categories)")
    return 0


def near_duplicate_pairs(entries: list[Entry]) -> list[tuple[str, Entry, Entry, float]]:
    """Pairs of rows in one category whose names look like the same resource.

    Single-token names overlap perfectly without describing the same thing
    (``data.gov.au`` and ``data.gov.gr`` both reduce to ``gov``), so they only
    count when one name contains the other and both rows point at one site.
    """
    stop = {"api", "the", "and", "for", "data", "server", "mcp", "service", "services", "public"}

    def tokens(name: str) -> set[str]:
        return {t for t in re.split(r"[^a-z0-9]+", name.casefold())
                if t and t not in stop and len(t) > 2}

    by_cat: dict[str, list[Entry]] = defaultdict(list)
    for e in entries:
        by_cat[e.category].append(e)

    fuzzy = []
    for cat, items in by_cat.items():
        for i, a in enumerate(items):
            for b in items[i + 1:]:
                ta, tb = tokens(a.name), tokens(b.name)
                if not ta or not tb:
                    continue
                if min(len(ta), len(tb)) < 2:
                    if not (ta <= tb or tb <= ta):
                        continue
                    if _registrable(a.url) != _registrable(b.url):
                        continue
                overlap = len(ta & tb) / len(ta | tb)
                if overlap < 0.8:
                    continue
                if ta == tb:
                    # Same words, different spelling only if one name contains
                    # the other; datos.gob.ar and datos.gob.cl share every token
                    # but are different national portals.
                    na = re.sub(r"[^a-z0-9]", "", a.name.casefold())
                    nb = re.sub(r"[^a-z0-9]", "", b.name.casefold())
                    if na not in nb and nb not in na:
                        continue
                fuzzy.append((cat, a, b, overlap))
    return fuzzy


def cmd_duplicates(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    exact = defaultdict(list)
    domain_name = defaultdict(list)
    for e in entries:
        exact[e.url.rstrip("/").lower()].append(e)
        host = urlsplit(e.url).netloc.lower().removeprefix("www.")
        key = re.sub(r"[^a-z0-9]", "", e.name.casefold())
        domain_name[(host, key)].append(e)

    groups = [g for g in exact.values() if len(g) > 1]
    groups += [g for g in domain_name.values() if len(g) > 1 and g not in groups]

    fuzzy = near_duplicate_pairs(entries)

    print(f"{len(groups)} same-URL or same-name group(s), "
          f"{len(fuzzy)} near-duplicate name pair(s)\n")
    for cat, a, b, score in fuzzy[:40]:
        print(f"  [{cat}] {a.name}  ~  {b.name}  ({score:.2f})")
    for g in groups:
        print(f"  {g[0].name}  [same url/name across: {', '.join(sorted({x.category for x in g}))}]")
        for e in g:
            print(f"     {e.category:24s} {e.url}")
    return 0


def cmd_stale(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    cutoff = dt.date.today() - dt.timedelta(days=args.days)
    stale = []
    for e in entries:
        if e.checked == "-":
            stale.append((e, "never checked"))
        elif dt.date.fromisoformat(e.checked) < cutoff:
            stale.append((e, f"checked {e.checked}"))
    print(f"{len(stale)} of {len(entries)} entries older than {args.days} days\n")
    for cat in sorted({e.category for e, _ in stale}):
        rows = [f"{e.name} ({e.checked})" for e, _ in stale if e.category == cat]
        print(f"  {cat:24s} {len(rows):3d}  " + ", ".join(rows[:6]) + (" ..." if len(rows) > 6 else ""))
    return 0


# ---------------------------------------------------------------- linkcheck

RETRY_STATUSES = {403, 405, 406, 501, 503}
GATED = {401, 402, 403, 429, 451}
BROKEN = {404, 410}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: D401
        return None


_OPENER = urllib.request.build_opener(_NoRedirect)


def _insecure_opener():
    """A second opener that ignores certificate validation.

    Some servers publish an incomplete chain that Windows rejects but a browser
    completes. A retry here separates 'certificate chain is broken' from 'server
    refuses the connection', which are very different maintenance actions.
    """
    context = ssl._create_unverified_context()  # noqa: S323 - diagnostic only
    return urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=context))
_HOST_GATE: dict[str, float] = {}
_GATE_LOCK = threading.Lock()


def _throttle(host: str, interval: float = 1.0) -> None:
    with _GATE_LOCK:
        last = _HOST_GATE.get(host, 0.0)
        wait = last + interval - time.monotonic()
        _HOST_GATE[host] = time.monotonic() + max(wait, 0.0)
    if wait > 0:
        time.sleep(wait)


PARKED_HOSTS = {
    "sedoparking.com", "parkingcrew.net", "dan.com", "afternic.com",
    "hugedomains.com", "buydomains.com", "parklogic.com", "above.com",
    "domainmarket.com", "undeveloped.com", "brandbucket.com", "domainsponsor.com",
}
PARKED_HINTS = (
    "domain is for sale", "buy this domain", "this domain may be for sale",
    "domain parking", "parked domain", "domain has expired", "this domain has expired",
)
DEPRECATED_HINTS = (
    "no longer available", "has been discontinued", "service has been discontinued",
    "has shut down", "service is discontinued", "end of life", "sunsetted",
    "api is deprecated", "this api has been retired",
)


def _classify_error(error: str | None) -> str:
    low = (error or "").lower()
    if "ssl" in low or "certificate" in low:
        return "tls-error"
    if "timed out" in low or "timeout" in low:
        return "timeout"
    if "name or service" in low or "getaddrinfo" in low or "no address" in low:
        return "dns"
    return "unreachable"


def _lower_headers(headers) -> dict:
    """HTTP header names are case-insensitive; servers are not consistent."""
    return {str(k).lower(): v for k, v in (headers or {}).items()}


def _fetch(url: str, method: str = "GET", timeout: float = 15.0,
           read_body: bool = False,
           insecure: bool = False) -> tuple[int | None, dict, bytes, str | None]:
    """One request, redirects NOT followed. Returns (status, headers, body, error)."""
    host = urlsplit(url).netloc
    headers = {"User-Agent": USER_AGENT,
               "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
               "Accept-Language": "en-US,en;q=0.8"}
    limit = read_body if isinstance(read_body, int) and not isinstance(read_body, bool) else 8192
    req = urllib.request.Request(url, method=method, headers=headers)
    opener = _insecure_opener() if insecure else _OPENER
    _throttle(host)
    try:
        with opener.open(req, timeout=timeout) as resp:
            body = resp.read(limit) if read_body else b""
            return int(resp.getcode()), _lower_headers(resp.headers), body, None
    except urllib.error.HTTPError as exc:
        body = b""
        if read_body:
            try:
                body = exc.read(limit)
            except Exception:  # noqa: BLE001
                body = b""
        return int(exc.code), _lower_headers(exc.headers), body, None
    except Exception as exc:  # noqa: BLE001
        return None, {}, b"", f"{type(exc).__name__}: {exc}"


def page_signals(body: bytes) -> tuple[str, str | None]:
    """Return (title, hint) from an HTML prefix. hint is 'parked' or 'deprecated'."""
    text = body.decode("utf-8", "replace")
    title = ""
    m = re.search(r"<title[^>]*>(.*?)</title>", text, re.I | re.S)
    if m:
        title = re.sub(r"\s+", " ", m.group(1)).strip()[:200]
    low = text.casefold()
    if any(h in low for h in PARKED_HINTS):
        return title, "parked"
    if any(h in low for h in DEPRECATED_HINTS):
        return title, "deprecated"
    return title, None


def _is_parked_host(url: str) -> bool:
    host = urlsplit(url).netloc.lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in PARKED_HOSTS)


def _defrag(url: str) -> str:
    """Drop the fragment: redirect targets are proposed as catalog cells."""
    parts = urlsplit(url)
    return parts._replace(fragment="").geturl()


SECOND_LEVEL = {"co", "com", "org", "net", "ac", "gov", "edu", "or", "ne", "go"}


def _registrable(url: str) -> str:
    """Approximate the registrable domain: last two labels, three for co.uk style."""
    host = urlsplit(url).netloc.lower().split(":")[0].removeprefix("www.")
    labels = host.split(".")
    if len(labels) >= 3 and labels[-2] in SECOND_LEVEL and len(labels[-1]) == 2:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def check_url(url: str, timeout: float = 15.0, max_hops: int = 5,
              deep: bool = False) -> dict:
    """Check one URL, following redirects so the report sees the real destination.

    deep=True also reads a bounded prefix of the final page to capture the title
    and to detect parking and retirement notices.
    """
    result = {"ok": False, "status": None, "kind": "unreachable", "error": None,
              "location": None, "final_url": url, "final_status": None,
              "title": None, "hint": None, "hops": 0, "method": "head",
              "moved_offsite": False, "elapsed_ms": 0}
    start = time.monotonic()
    current = url

    status, headers, body, error = _fetch(current, "HEAD", timeout)
    method = "head"
    if status is None or status in RETRY_STATUSES or status >= 400:
        time.sleep(0.5)
        status, headers, body, error = _fetch(current, "GET", timeout)
        method = "get"

    hops = 0
    while status is not None and 300 <= status < 400 and hops < max_hops:
        location = headers.get("location")
        if not location:
            break
        current = _defrag(urljoin(current, location))
        hops += 1
        time.sleep(0.3)
        status, headers, body, error = _fetch(current, method, timeout)
        if status is None or status in RETRY_STATUSES or status >= 400:
            time.sleep(0.4)
            status, headers, body, error = _fetch(current, "GET", timeout)
            method = "get"

    result.update(hops=hops, final_url=current, method=method)
    moved = current.rstrip("/") != url.rstrip("/")
    result["moved_offsite"] = bool(moved and _registrable(current) != _registrable(url))

    if status is None:
        result["error"] = error
        result["kind"] = _classify_error(error)
        if result["kind"] == "tls-error":
            time.sleep(0.4)
            status2, headers2, body2, error2 = _fetch(current, "GET", timeout, True, insecure=True)
            if status2 is not None and 200 <= status2 < 400:
                result.update(status=status2, final_status=status2, kind="tls-chain", ok=True,
                              error=f"certificate chain rejected by the client store ({error}); "
                                    f"page answers {status2} without validation")
                headers, body, status = headers2, body2, status2
    elif 200 <= status < 300:
        result.update(ok=True, status=status, final_status=status,
                      kind="moved" if moved else "ok",
                      location=current if moved else None)
    elif 300 <= status < 400:
        result.update(status=status, kind="redirect",
                      location=urljoin(current, headers.get("location") or ""))
    elif status in GATED:
        result.update(status=status, final_status=status, kind="gated",
                      error=f"HTTP {status}")
    elif status in BROKEN:
        result.update(status=status, final_status=status, kind="broken",
                      error=f"HTTP {status}")
    else:
        result.update(status=status, final_status=status, kind="error",
                      error=f"HTTP {status}")

    if _is_parked_host(current):
        result.update(ok=False, kind="dead-parked", error="redirects to a domain parking host")

    if deep and result["kind"] in {"ok", "moved", "gated"}:
        if not body:
            time.sleep(0.2)
            _, _, body, _ = _fetch(current, "GET", timeout, read_body=True)
        title, hint = page_signals(body)
        result["title"] = title or None
        result["hint"] = hint
        if hint == "parked":
            result.update(ok=False, kind="dead-parked",
                          error=f"page reads as a parked domain ({title or 'no title'})")

    result["elapsed_ms"] = int((time.monotonic() - start) * 1000)
    return result


def cmd_linkcheck(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    if args.category:
        entries = [e for e in entries if e.category == args.category]
    if args.limit:
        random.Random(args.seed).shuffle(entries)
        entries = entries[: args.limit]

    jobs = []
    for e in entries:
        jobs.append((e, "website", e.url))
        if e.docs and e.docs.rstrip("/") != e.url.rstrip("/"):
            jobs.append((e, "docs", e.docs))

    print(f"checking {len(jobs)} URLs from {len(entries)} entries "
          f"(workers={args.workers}, timeout={args.timeout}s)")
    results = []
    done = 0
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(check_url, url, args.timeout): (e, f, url) for e, f, url in jobs}
        for fut in futures.as_completed(futs):
            e, kind, url = futs[fut]
            r = fut.result()
            done += 1
            results.append({"name": e.name, "category": e.category, "field": kind,
                            "url": url, **r})
            if done % 100 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    results.sort(key=lambda r: (r["category"], r["name"].casefold()))
    REPORT_DIR.mkdir(exist_ok=True)
    stamp = dt.date.today().isoformat()
    out = Path(args.out).resolve() if args.out else REPORT_DIR / f"linkcheck-{stamp}.json"
    out.write_text(json.dumps({
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "catalog_entries": len(entries),
        "urls_checked": len(results),
        "summary": dict(Counter(r["kind"] for r in results)),
        "results": results,
    }, indent=1), encoding="utf-8")

    summary = Counter(r["kind"] for r in results)
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(summary.items())))
    try:
        print(f"wrote {out.relative_to(ROOT)}")
    except ValueError:
        print(f"wrote {out}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    problems = Problems()
    entries = load(problems, strict=True)
    reports = sorted(REPORT_DIR.glob("linkcheck-*.json")) + sorted(REPORT_DIR.glob("verify-*.json"))
    if not reports:
        print("no link check report found, run: python scripts/catalog.py verify")
        return 2
    last = max((json.loads(p.read_text(encoding="utf-8")) for p in reports),
               key=lambda d: d.get("generated", ""))
    age = (dt.date.today() - dt.date.fromisoformat(last["generated"][:10])).days

    by_url = {(r["category"], r["name"], r["field"]): r for r in last["results"]}
    interesting = defaultdict(list)
    for r in last["results"]:
        if r["kind"] != "ok":
            interesting[r["kind"]].append(r)
    if interesting.get("moved"):
        offsite = [r for r in interesting["moved"] if r.get("moved_offsite")]
        interesting["moved-offsite"] = offsite
        interesting["moved"] = [r for r in interesting["moved"] if not r.get("moved_offsite")]

    lines = [
        f"# Maintenance report {dt.date.today().isoformat()}",
        "",
        f"Catalog: {len(entries)} entries, {len(table_files())} category files.",
        f"Link check: {last['generated'][:10]} ({age} days old), "
        f"{last['urls_checked']} URLs, " + ", ".join(f"{k} {v}" for k, v in sorted(last["summary"].items())) + ".",
        f"Validation: {len(problems.errors)} errors, {len(problems.warnings)} warnings.",
        "",
        "This report is a review document. Nothing is changed automatically.",
        "",
    ]
    if age > 14:
        lines += [f"> Link check data is {age} days old. Re-run linkcheck before acting on it.", ""]

    titles = {
        "broken": "Broken (404/410): candidate for correction or removal",
        "dead-parked": "Dead: resolves to a parked or expired domain",
        "moved": "Moved: propose updating the URL to the new location",
        "moved-offsite": "Moved to a different domain: confirm in a browser before editing",
        "redirect": "Redirect loop or unresolved redirect",
        "gated": "Gated (401/402/403/429/451): keep, note the access requirement",
        "dns": "DNS failure: domain likely retired, needs a human decision",
        "tls-error": "TLS/certificate error: often bot protection, re-check in a browser",
        "tls-chain": "Certificate chain incomplete: a browser completes it, no action needed",
        "timeout": "Timeout: re-check before acting",
        "error": "Server error (5xx): transient, re-check before acting",
        "unreachable": "Unreachable transport error: re-check before acting",
    }
    props = []
    for kind in ["broken", "dead-parked", "moved", "moved-offsite", "redirect", "gated", "dns",
                 "tls-error", "timeout", "error", "unreachable"]:
        rows = interesting.get(kind, [])
        if not rows:
            continue
        lines += [f"## {titles.get(kind, kind)} ({len(rows)})", ""]
        for r in rows[: args.max_per_section]:
            detail = r.get("location") or r.get("error") or ""
            lines.append(f"- `{r['category']}` **{r['name']}** {r['field']} <{r['url']}> "
                         f"[{r.get('status') or ''}] {detail}".rstrip())
            if kind in {"broken", "dead-parked", "moved", "dns"}:
                entry = next((e for e in entries if e.category == r["category"] and e.name == r["name"]), None)
                if entry:
                    props.append((entry, kind, r))
        if len(rows) > args.max_per_section:
            lines.append(f"- ... and {len(rows) - args.max_per_section} more (see the JSON report)")
        lines.append("")

    stale = [e for e in entries
             if e.checked == "-" or
             (dt.date.today() - dt.date.fromisoformat(e.checked)).days > args.stale_days]
    lines += [f"## Metadata older than {args.stale_days} days ({len(stale)})", ""]
    lines.append(f"{len([e for e in entries if e.checked == '-'])} entries have no verification date. "
                 f"The catalog is link-checked regularly; dates are only set when someone read the official documentation.")
    lines.append("")

    dups = defaultdict(list)
    for e in entries:
        dups[e.url.rstrip("/").lower()].append(e)
    dup_groups = [g for g in dups.values() if len(g) > 1]
    lines += [f"## Possible duplicates ({len(dup_groups)})", ""]
    for g in dup_groups[: args.max_per_section]:
        lines.append("- " + " / ".join(f"{x.category}:{x.name}" for x in g) + f" <{g[0].url}>")
    lines.append("")

    if problems.errors:
        lines += ["## Validation errors", ""] + [f"- {x}" for x in problems.errors] + [""]

    if props:
        lines += ["## Proposed edits (not applied)", ""]
        for entry, kind, r in props[: args.max_per_section]:
            current = next((ln for ln in (ROOT / "catalog" / f"{entry.category}.md").read_text(encoding="utf-8").splitlines()
                            if f"[{entry.name}](" in ln), "")
            target = r.get("final_url") or r.get("location") or ""
            if kind == "moved" and target.startswith(("http://", "https://")):
                cell = "website" if r.get("field") == "website" else "docs"
                anchor = f"[{entry.name}]({entry.url})" if cell == "website" else f"[docs]({entry.docs})"
                new = current.replace(anchor, anchor.replace(
                    entry.url if cell == "website" else entry.docs, target))
                lines += [f"`catalog/{entry.category}.md` line {entry.line}: moved ({cell})",
                          "```diff", f"- {current}", f"+ {new}", "```"]
            else:
                lines += [f"`catalog/{entry.category}.md` line {entry.line}: {kind}", "```diff",
                          f"- {current}", "```"]
        lines.append("")

    REPORT_DIR.mkdir(exist_ok=True)
    out = REPORT_DIR / f"maintenance-{dt.date.today().isoformat()}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  {len(problems.errors)} validation errors, {len(interesting.get('broken', []))} broken, "
          f"{len(interesting.get('dead-parked', []))} parked, {len(interesting.get('moved', []))} moved, "
          f"{len(stale)} stale, {len(dup_groups)} duplicate groups")
    return 0


def _name_tokens(name: str) -> list[str]:
    stop = {"api", "apis", "the", "and", "for", "data", "open", "public", "service",
            "server", "mcp", "dataset", "portal", "online", "free"}
    return [t for t in re.split(r"[^a-z0-9]+", name.casefold())
            if len(t) >= 4 and t not in stop]


def _title_matches(name: str, title: str | None, url: str) -> bool | None:
    """None when there is nothing to compare, else whether the page looks like the row."""
    tokens = _name_tokens(name)
    if not title or not tokens:
        return None
    haystack = f"{title} {url}".casefold()
    return any(t in haystack for t in tokens)


BOT_WALL_MARKERS = (
    "just a moment", "access denied", "attention required", "request rate threshold",
    "verify you are human", "are you a robot", "ddos protection", "cloudflare",
    "checking your browser", "enable javascript and cookies", "security checkpoint",
    "403 forbidden", "request blocked", "bot protection",
    "доступ заблоковано", "request could not be satisfied", "service unavailable",
)


def _bot_wall(title: str | None) -> bool:
    """True when a 403/429 page is a bot challenge rather than an auth gate."""
    text = (title or "").casefold()
    return any(marker in text for marker in BOT_WALL_MARKERS)


def _newest_report(pattern: str, directory: Path = REPORT_DIR) -> dict | None:
    """Load the report with the latest ``generated`` stamp, not the latest name.

    ``verify-2026-11-07-final.json`` sorts before ``verify-2026-11-07.json``, so a
    filename sort silently summarizes the older run.
    """
    reports = list(directory.glob(pattern))
    if not reports:
        return None
    return max((json.loads(p.read_text(encoding="utf-8")) for p in reports),
               key=lambda d: d.get("generated", ""))


def cmd_triage(args: argparse.Namespace) -> int:
    """Turn the newest verify report into a decision queue grouped by action."""
    report = _newest_report("verify-*.json")
    if report is None:
        print("no verify report found, run: python scripts/catalog.py verify")
        return 2
    entries = {(e.category, e.name): e for e in load(Problems(), strict=False)}

    buckets: dict[str, list[dict]] = defaultdict(list)
    for r in report["results"]:
        entry = entries.get((r["category"], r["name"]))
        if entry is None:
            continue
        kind = r["kind"]
        action = None
        if kind == "tls-chain":
            continue
        if kind in {"broken", "dead-parked", "dns"}:
            action = "remove-or-replace"
        elif kind == "moved" and r.get("moved_offsite"):
            action = "confirm-new-domain"
        elif kind == "moved":
            action = "update-url"
        elif kind == "gated" and entry.auth == "None":
            if r.get("status") in (403, 429) and _bot_wall(r.get("title")):
                action = "bot-gated"
            else:
                action = "auth-mismatch"
        elif r.get("hint") == "deprecated":
            action = "retired"
        elif kind in {"timeout", "tls-error", "error", "unreachable", "redirect"}:
            action = "recheck"
        else:
            matched = _title_matches(r["name"], r.get("title"), r.get("final_url") or r["url"])
            if matched is False:
                action = "title-mismatch"
        if action:
            buckets[action].append({
                "category": r["category"], "name": r["name"], "type": entry.type,
                "field": r["field"], "url": r["url"], "kind": kind,
                "status": r.get("status"), "final_url": r.get("final_url"),
                "title": r.get("title"), "auth": entry.auth, "access": entry.access,
                "checked": entry.checked, "action": action,
            })

    order = ["remove-or-replace", "retired", "confirm-new-domain", "auth-mismatch",
             "bot-gated", "title-mismatch", "update-url", "recheck"]
    stamp = dt.date.today().isoformat()
    out_json = REPORT_DIR / f"triage-{stamp}.json"
    out_json.write_text(json.dumps({"generated": report["generated"],
                                    "counts": {k: len(buckets.get(k, [])) for k in order},
                                    "buckets": {k: buckets.get(k, []) for k in order}},
                                   indent=1), encoding="utf-8")

    lines = [f"# Triage {stamp}", "",
             f"Source: verify report generated {report['generated']}, "
             f"{report['urls_checked']} URLs checked.", "",
             "Grouped by the decision the row needs. Nothing here is applied automatically.", ""]
    for key in order:
        rows = buckets.get(key, [])
        if not rows:
            continue
        lines += [f"## {key} ({len(rows)})", ""]
        for r in rows[: args.max_per_section]:
            detail = r["title"] or r.get("final_url") or ""
            lines.append(f"- `{r['category']}` **{r['name']}** [{r['field']}] "
                         f"<{r['url']}> -> {detail}"[:300])
        if len(rows) > args.max_per_section:
            lines.append(f"- ... and {len(rows) - args.max_per_section} more (see the JSON)")
        lines.append("")
    out_md = REPORT_DIR / f"triage-{stamp}.md"
    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"{report['urls_checked']} URLs from verify report {report['generated'][:10]}")
    for key in order:
        print(f"  {key:20s} {len(buckets.get(key, [])):4d}")
    print(f"\nwrote {out_md.relative_to(ROOT)} and {out_json.relative_to(ROOT)}")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Deep verification: status, final URL, page title and retirement signals."""
    entries = load(Problems(), strict=False)
    if args.category:
        entries = [e for e in entries if e.category == args.category]
    if args.type:
        entries = [e for e in entries if e.type == args.type]
    if args.limit:
        random.Random(args.seed).shuffle(entries)
        entries = entries[: args.limit]

    jobs = []
    for e in entries:
        jobs.append((e, "website", e.url))
        if e.docs and e.docs.rstrip("/") != e.url.rstrip("/"):
            jobs.append((e, "docs", e.docs))

    print(f"verifying {len(jobs)} URLs from {len(entries)} entries "
          f"(workers={args.workers}, timeout={args.timeout}s)", flush=True)
    results = []
    done = 0
    with futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(check_url, url, args.timeout, 5, True): (e, f, url)
                for e, f, url in jobs}
        for fut in futures.as_completed(futs):
            e, kind, url = futs[fut]
            r = fut.result()
            done += 1
            results.append({"name": e.name, "category": e.category, "type": e.type,
                            "field": kind, "url": url, **r})
            if done % 100 == 0:
                print(f"  {done}/{len(jobs)}", flush=True)

    results.sort(key=lambda r: (r["category"], r["name"].casefold()))
    stamp = dt.date.today().isoformat()
    out = Path(args.out).resolve() if args.out else REPORT_DIR / f"verify-{stamp}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "generated": dt.datetime.now().isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "catalog_entries": len(entries),
        "urls_checked": len(results),
        "summary": dict(Counter(r["kind"] for r in results)),
        "results": results,
    }, indent=1), encoding="utf-8")

    summary = Counter(r["kind"] for r in results)
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(summary.items())))
    retired = [r for r in results if r.get("hint") == "deprecated"]
    print(f"{len(retired)} page(s) carry retirement or deprecation wording")
    try:
        print(f"wrote {out.relative_to(ROOT)}")
    except ValueError:
        print(f"wrote {out}")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="check table format, values, order and navigation")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("stats", help="counts by category, type, access and source")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("export", help="write a machine-readable copy")
    p.add_argument("--format", choices=["jsonl", "json", "csv"], default="jsonl")
    p.add_argument("--out")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("linkcheck", help="HTTP check every website and docs URL")
    p.add_argument("--limit", type=int, default=0, help="random sample size (0 = all)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--category")
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=15.0)
    p.add_argument("--out")
    p.set_defaults(func=cmd_linkcheck)

    p = sub.add_parser("report", help="build a maintenance report from the last link check")
    p.add_argument("--max-per-section", type=int, default=40)
    p.add_argument("--stale-days", type=int, default=365)
    p.set_defaults(func=cmd_report)

    p = sub.add_parser("verify", help="deep check: final URL, page title, retirement signals")
    p.add_argument("--limit", type=int, default=0, help="random sample size (0 = all)")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--category")
    p.add_argument("--type", choices=sorted(TYPES))
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--timeout", type=float, default=20.0)
    p.add_argument("--out")
    p.set_defaults(func=cmd_verify)

    p = sub.add_parser("shortlist", help="write docs/no-auth.md from the keyless subset")
    p.set_defaults(func=cmd_shortlist)

    p = sub.add_parser("triage", help="turn the newest verify report into a decision queue")
    p.add_argument("--max-per-section", type=int, default=60)
    p.set_defaults(func=cmd_triage)

    p = sub.add_parser("duplicates", help="list entries sharing a URL or a name on the same domain")
    p.set_defaults(func=cmd_duplicates)

    p = sub.add_parser("stale", help="entries with old or missing verification dates")
    p.add_argument("--days", type=int, default=365)
    p.set_defaults(func=cmd_stale)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
