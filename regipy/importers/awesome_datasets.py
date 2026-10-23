"""Importer for awesomedata/awesome-public-datasets (MIT).

The published README.rst is generated from apd-core YAML records. Each bullet is
"* |ICON| `Title - Description <url>`_ [`Meta <path>`]_" grouped under a section
heading underlined with dashes. The upstream project states most datasets are
free but some are not, and does not record licences, so licence and pricing stay
unknown unless a provider policy applies later.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .. import schema
from ..models import new_record

SOURCE = "awesome-public-datasets"
SOURCE_URL = "https://github.com/awesomedata/awesome-public-datasets"
SOURCE_LICENSE = "MIT"

BULLET_RE = re.compile(r"^\*\s+\|[A-Z_]+\|\s*`(?P<body>.+?)`_", re.S)
URL_RE = re.compile(r"<(?P<url>https?://[^>]+)>")
META_RE = re.compile(r"`Meta\s+<(?P<url>[^>]+)>`")
UNDERLINE_RE = re.compile(r"^(?P<char>[-=])\1{2,}\s*$")


def _split_title(body: str) -> tuple[str, str | None, bool]:
    text = re.sub(r"\s+", " ", body).strip()
    text = text.replace("\\", "")
    truncated = text.endswith("[...]")
    if " - " in text:
        title, description = text.split(" - ", 1)
        description = description.strip()
        if description.endswith("[...]"):
            description = description[:-5].strip()
        return title.strip(), (description or None), truncated
    return text, None, truncated


def parse(readme: str) -> list[dict[str, Any]]:
    lines = readme.splitlines()
    section: str | None = None
    records: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    for index, line in enumerate(lines):
        if UNDERLINE_RE.match(line.strip()) and index > 0:
            heading = lines[index - 1].strip()
            if heading and not heading.startswith("*") and len(heading) < 80:
                section = heading
            continue
        match = BULLET_RE.match(line.strip())
        if not match or not section:
            continue
        body = match.group("body")
        url_match = URL_RE.search(body)
        if not url_match:
            continue
        url = url_match.group("url")
        title, description, truncated = _split_title(body[: url_match.start()].strip())
        meta = META_RE.search(line)
        upstream_id = None
        if meta:
            upstream_id = meta.group("url").split("/core/", 1)[-1].strip("/")
        if not title:
            continue
        key = (url.lower(), title.lower())
        if key in seen:
            continue
        seen.add(key)
        rec = new_record(
            kind="dataset",
            name=title,
            description=description,
            category=schema.map_category("awesome_datasets", section),
            type_="download" if "." in url.rsplit("/", 1)[-1] else "dataset",
            website=url,
            access_model="unknown",
            pricing_model="unknown",
            tags=[section.lower().replace("+", "-").replace(" ", "-")],
            source=SOURCE,
            source_url=SOURCE_URL,
            source_license=SOURCE_LICENSE,
            upstream_id=upstream_id,
            notes="Description truncated in the upstream catalog." if truncated else None,
        )
        rec["coverage"] = {"geographic": None, "temporal": None}
        records.append(rec)
    return records


def parse_file(path: Path) -> list[dict[str, Any]]:
    return parse(path.read_text(encoding="utf-8"))
