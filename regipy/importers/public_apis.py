"""Importer for public-apis/public-apis (MIT).

The upstream project publishes a single README with one markdown table per
category. Columns are API, Description, Auth, HTTPS, CORS. Pricing, licensing
and coverage are not recorded upstream, so they stay unknown; the fact that a
service is listed as a free API is captured in pricing.free_tier_indicated with
basis "upstream_catalog".
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .. import schema
from ..models import new_record

SOURCE = "public-apis"
SOURCE_URL = "https://github.com/public-apis/public-apis"
SOURCE_LICENSE = "MIT"

SECTION_RE = re.compile(r"^###\s+(?P<name>.+?)\s*$")
LINK_RE = re.compile(r"\[(?P<label>[^\]]+)\]\((?P<url>[^)\s]+)\)")
SCHEMES = {"": "public", "no": "public", "apikey": "api_key", "oauth": "oauth",
           "x-mashape-key": "api_key", "user-agent": "public", "yes": "api_key"}

AUTH_NOTES = {
    "X-Mashape-Key": "Mashape/RapidAPI key header",
    "User-Agent": "Requires a descriptive User-Agent header, no key",
}


def _cells(line: str) -> list[str]:
    line = line.strip().strip("|")
    line = line.replace("\\|", "\x00")
    return [cell.replace("\x00", "|").strip() for cell in line.split("|")]


def parse(readme: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    section: str | None = None
    seen: set[tuple[str, str]] = set()

    for raw in readme.splitlines():
        line = raw.rstrip("\r")
        match = SECTION_RE.match(line)
        if match:
            section = match.group("name")
            # Only real catalog sections count. The README also carries
            # promotional headings with the same level.
            if section not in schema.load_taxonomy()["public_apis"]:
                section = None
            continue
        if not line.startswith("|") or section is None:
            continue
        cells = _cells(line)
        if len(cells) != 5:
            continue
        if cells[0].lower().startswith("api") or set(cells[3].lower()) <= {"-", ":"}:
            continue
        link = LINK_RE.search(cells[0])
        if not link:
            continue
        name = link.group("label").strip()
        url = link.group("url").strip()
        description = cells[1].strip() or None
        auth_raw = cells[2].strip().strip("`")
        https = cells[3].strip().lower()
        cors = cells[4].strip().lower()

        access = SCHEMES.get(auth_raw.lower(), "unknown")
        note = AUTH_NOTES.get(auth_raw)
        if access == "unknown" and auth_raw:
            note = f"Upstream auth column: {auth_raw}"
        if cells[3].strip().lower() not in ("yes", "no", ""):
            continue

        dedupe = (url.lower(), name.lower())
        if dedupe in seen:
            continue
        seen.add(dedupe)

        rec = new_record(
            kind="api",
            name=name,
            description=description,
            category=schema.map_category("public_apis", section),
            type_="rest",
            website=url,
            access_model=access,
            access_notes=note,
            pricing_model="unknown",
            pricing_basis="upstream_catalog",
            free_tier_indicated=True if access in ("public", "api_key", "oauth") else None,
            https=True if https == "yes" else (False if https == "no" else None),
            cors="yes" if cors == "yes" else ("no" if cors == "no" else "unknown"),
            tags=[section.lower().replace(" & ", "-").replace(" ", "-")],
            source=SOURCE,
            source_url=SOURCE_URL,
            source_license=SOURCE_LICENSE,
            upstream_id=f"{section}: {name}",
            notes="Listed in the public-apis catalog as a free API; tier limits are not recorded upstream.",
        )
        if access == "public" and auth_raw == "":
            rec["access"]["model"] = "public"
        records.append(rec)
    return records


def parse_file(path: Path) -> list[dict[str, Any]]:
    return parse(path.read_text(encoding="utf-8"))
