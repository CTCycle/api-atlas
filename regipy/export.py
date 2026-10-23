"""Export helpers for registry records."""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Any, Iterable

from . import schema

COLUMNS: list[str] = [
    "id",
    "kind",
    "name",
    "description",
    "category",
    "type",
    "provider.id",
    "provider.name",
    "provider.domain",
    "urls.website",
    "urls.documentation",
    "urls.spec",
    "access.model",
    "pricing.model",
    "pricing.free_tier_indicated",
    "pricing.free_tier_limits",
    "license.name",
    "license.spdx",
    "license.commercial_use",
    "coverage.geographic",
    "coverage.temporal",
    "formats",
    "update_frequency",
    "status",
    "verification.confidence",
    "verification.last_verified",
    "verification.method",
    "verification.http_status",
    "provenance",
    "tags",
]


def _stringify(value: Any, path: str | None = None) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, dict):
                if path == "provenance":
                    source = item.get("source")
                    parts.append("" if source is None else str(source))
                else:
                    parts.append(json.dumps(item, ensure_ascii=False, sort_keys=True))
            else:
                parts.append("" if item is None else str(item))
        return "; ".join(parts)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def flatten(record: dict[str, Any], columns: Iterable[str] | None = None) -> dict[str, Any]:
    """Flatten nested record paths into a single level dictionary."""
    selected = list(columns) if columns is not None else list(COLUMNS)
    result: dict[str, Any] = {}
    for column in selected:
        value = schema.get_path(record, column)
        if column == "provenance":
            value = _stringify(value, column)
        else:
            value = _stringify(value)
        result[column] = value
    return result


def _records_to_rows(records: Iterable[dict[str, Any]], columns: list[str] | None) -> tuple[list[str], list[dict[str, Any]]]:
    selected = list(columns) if columns is not None else list(COLUMNS)
    rows = [flatten(record, selected) for record in records]
    return selected, rows


def to_csv(records: Iterable[dict[str, Any]], columns: Iterable[str] | None = None) -> str:
    selected = list(columns) if columns is not None else list(COLUMNS)
    rows = [flatten(record, selected) for record in records]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=selected, extrasaction="ignore", lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def to_jsonl(records: Iterable[dict[str, Any]], columns: Iterable[str] | None = None) -> str:
    selected = list(columns) if columns is not None else list(COLUMNS)
    lines: list[str] = []
    for record in records:
        row = flatten(record, selected)
        lines.append(json.dumps(row, ensure_ascii=False))
    return "\n".join(lines) + ("\n" if lines else "")


def to_json(records: Iterable[dict[str, Any]]) -> str:
    return json.dumps(list(records), ensure_ascii=False, indent=2) + "\n"


def to_markdown(records: Iterable[dict[str, Any]], columns: Iterable[str] | None = None) -> str:
    selected = list(columns) if columns is not None else list(COLUMNS)
    rows = [flatten(record, selected) for record in records]
    lines: list[str] = []
    header = "| " + " | ".join(selected) + " |"
    separator = "| " + " | ".join("---" for _ in selected) + " |"
    lines.append(header)
    lines.append(separator)
    for row in rows:
        values = [str(row.get(column, "")).replace("|", "\\|").replace("\n", " ") for column in selected]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + ("\n" if lines else "")


def export(
    records: Iterable[dict[str, Any]],
    *,
    fmt: str = "csv",
    out: Any = None,
    columns: Iterable[str] | None = None,
) -> str:
    if fmt in ("csv",):
        text = to_csv(records, columns)
    elif fmt in ("jsonl", "jsonl"):
        text = to_jsonl(records, columns)
    elif fmt in ("json",):
        text = to_json(records)
    elif fmt in ("md", "markdown"):
        text = to_markdown(records, columns)
    else:
        raise ValueError(f"unsupported export format: {fmt}")
    if out is not None:
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    return text
