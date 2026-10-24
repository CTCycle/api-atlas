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
from urllib.parse import urlsplit

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


def cmd_export(args: argparse.Namespace) -> int:
    entries = load(Problems(), strict=False)
    DATA_DIR.mkdir(exist_ok=True)
    if args.format == "jsonl":
        out = Path(args.out) if args.out else DATA_DIR / "catalog.jsonl"
        with out.open("w", encoding="utf-8", newline="\n") as fh:
            for e in entries:
                fh.write(json.dumps({
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
                    "checked": None if e.checked == "-" else e.checked,
                }, sort_keys=True, ensure_ascii=False) + "\n")
    else:
        out = Path(args.out) if args.out else DATA_DIR / "catalog.csv"
        with out.open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["id", "name", "type", "category", "description", "website",
                        "docs", "access", "auth", "license", "source", "checked"])
            for e in entries:
                w.writerow([e.slug, e.name, e.type, e.category, e.description, e.url,
                            e.docs, e.access, e.auth, e.license, e.source,
                            "" if e.checked == "-" else e.checked])
    print(f"wrote {out} ({len(entries)} entries)")
    return 0


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
    print(f"{len(groups)} possible duplicate group(s)\n")
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
_HOST_GATE: dict[str, float] = {}
_GATE_LOCK = threading.Lock()


def _throttle(host: str, interval: float = 1.0) -> None:
    with _GATE_LOCK:
        last = _HOST_GATE.get(host, 0.0)
        wait = last + interval - time.monotonic()
        _HOST_GATE[host] = time.monotonic() + max(wait, 0.0)
    if wait > 0:
        time.sleep(wait)


def check_url(url: str, timeout: float = 15.0) -> dict:
    host = urlsplit(url).netloc
    ctx = ssl.create_default_context()
    result = {"ok": False, "status": None, "kind": "unreachable", "error": None,
              "location": None, "method": "head", "elapsed_ms": 0}
    start = time.monotonic()

    def fetch(method: str) -> tuple[int | None, str | None, str | None]:
        headers = {"User-Agent": USER_AGENT, "Accept": "*/*",
                   "Accept-Language": "en-US,en;q=0.8"}
        if method == "GET":
            headers["Range"] = "bytes=0-2048"
        req = urllib.request.Request(url, method=method, headers=headers)
        _throttle(host)
        try:
            with _OPENER.open(req, timeout=timeout) as resp:
                return int(resp.getcode()), None, None
        except urllib.error.HTTPError as exc:
            return int(exc.code), exc.headers.get("Location"), None
        except Exception as exc:  # noqa: BLE001
            return None, None, f"{type(exc).__name__}: {exc}"

    status, location, error = fetch("HEAD")
    if status is None or status in RETRY_STATUSES or (status or 0) >= 400:
        time.sleep(0.5)
        status, location, error = fetch("GET")
        result["method"] = "get"

    if status is None:
        result["error"] = error
        low = (error or "").lower()
        if "ssl" in low or "certificate" in low:
            result["kind"] = "tls-error"
        elif "timed out" in low or "timeout" in low:
            result["kind"] = "timeout"
        elif "name or service" in low or "getaddrinfo" in low:
            result["kind"] = "dns"
        else:
            result["kind"] = "unreachable"
    elif 200 <= status < 300:
        result.update(ok=True, status=status, kind="ok")
    elif 300 <= status < 400:
        result.update(status=status, kind="redirect", location=location)
    elif status in GATED:
        result.update(status=status, kind="gated", error=f"HTTP {status}")
    elif status in BROKEN:
        result.update(status=status, kind="broken", error=f"HTTP {status}")
    else:
        result.update(status=status, kind="error", error=f"HTTP {status}")
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
    out = Path(args.out) if args.out else REPORT_DIR / f"linkcheck-{stamp}.json"
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
    print(f"wrote {out.relative_to(ROOT)}")
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    problems = Problems()
    entries = load(problems, strict=True)
    reports = sorted(REPORT_DIR.glob("linkcheck-*.json"))
    if not reports:
        print("no linkcheck report found, run: python scripts/catalog.py linkcheck")
        return 2
    last = json.loads(reports[-1].read_text(encoding="utf-8"))
    age = (dt.date.today() - dt.date.fromisoformat(last["generated"][:10])).days

    by_url = {(r["category"], r["name"], r["field"]): r for r in last["results"]}
    interesting = defaultdict(list)
    for r in last["results"]:
        if r["kind"] != "ok":
            interesting[r["kind"]].append(r)

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
        "redirect": "Redirected: propose updating the URL to the new location",
        "gated": "Gated (401/402/403/429/451): keep, note the access requirement",
        "dns": "DNS failure: domain likely retired, needs a human decision",
        "tls-error": "TLS/certificate error: often bot protection, re-check in a browser",
        "timeout": "Timeout: re-check before acting",
        "error": "Server error (5xx): transient, re-check before acting",
        "unreachable": "Unreachable transport error: re-check before acting",
    }
    props = []
    for kind in ["broken", "redirect", "gated", "dns", "tls-error", "timeout", "error", "unreachable"]:
        rows = interesting.get(kind, [])
        if not rows:
            continue
        lines += [f"## {titles.get(kind, kind)} ({len(rows)})", ""]
        for r in rows[: args.max_per_section]:
            detail = r.get("location") or r.get("error") or ""
            lines.append(f"- `{r['category']}` **{r['name']}** {r['field']} <{r['url']}> "
                         f"[{r.get('status') or ''}] {detail}".rstrip())
            if kind in {"broken", "redirect", "dns"}:
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
            if kind == "redirect" and r.get("location"):
                new = current.replace(entry.url, r["location"])
                lines += [f"`catalog/{entry.category}.md` line {entry.line}: redirect", "```diff",
                          f"- {current}", f"+ {new}", "```"]
            else:
                lines += [f"`catalog/{entry.category}.md` line {entry.line}: {kind}", "```diff",
                          f"- {current}", "```"]
        lines.append("")

    REPORT_DIR.mkdir(exist_ok=True)
    out = REPORT_DIR / f"maintenance-{dt.date.today().isoformat()}.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}")
    print(f"  {len(problems.errors)} validation errors, {len(interesting.get('broken', []))} broken, "
          f"{len(interesting.get('redirect', []))} redirected, {len(stale)} stale, {len(dup_groups)} duplicate groups")
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
    p.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
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

    p = sub.add_parser("duplicates", help="list entries sharing a URL or a name on the same domain")
    p.set_defaults(func=cmd_duplicates)

    p = sub.add_parser("stale", help="entries with old or missing verification dates")
    p.add_argument("--days", type=int, default=365)
    p.set_defaults(func=cmd_stale)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
