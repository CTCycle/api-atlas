"""Importer for the APIs.guru openapi-directory (CC0-1.0).

list.json is a provider keyed map. For each provider the preferred version
carries an OpenAPI/AsyncAPI document info block: title, description, contact,
licence, terms of service, categories, spec URLs and the origin document.
Everything else (pricing, access model, coverage) is not present upstream and
stays unknown.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .. import schema
from ..models import new_record

SOURCE = "apis-guru"
SOURCE_URL = "https://apis.guru"
SOURCE_LICENSE = "CC0-1.0"

MARKDOWN_LINK_RE = re.compile(r"\[([^\]]*)\]\((?:[^()]|\([^()]*\))*\)")


def _clean_description(text: str | None) -> str | None:
    if not text:
        return None
    text = MARKDOWN_LINK_RE.sub(r"\1", text)
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > 1000:
        text = text[:997].rstrip() + "..."
    return text or None


def _first_category(info: dict[str, Any]) -> str:
    for value in info.get("x-apisguru-categories") or []:
        if isinstance(value, str) and len(value) > 2:
            return schema.map_category("apis_guru", value)
    return "unknown"


def _provider_url(info: dict[str, Any], provider: str) -> str | None:
    contact = info.get("contact") or {}
    for candidate in (contact.get("url"), contact.get("email")):
        if candidate and str(candidate).startswith("http"):
            return str(candidate)
    if "." in provider and " " not in provider:
        return f"https://{provider}"
    return None


def parse(payload: dict[str, Any], version: str | None = None) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for provider, entry in payload.items():
        preferred = entry.get("preferred")
        versions = entry.get("versions") or {}
        if preferred not in versions:
            continue
        data = versions[preferred]
        info = data.get("info") or {}
        title = (info.get("title") or provider).strip()
        spec_url = data.get("swaggerUrl") or data.get("openapiYamlUrl") or data.get("swaggerYamlUrl")
        origins = info.get("x-origin") or []
        origin_url = origins[0].get("url") if origins else None
        licence = info.get("license") or {}
        update_frequency = "unknown"
        rec = new_record(
            kind="api",
            name=title,
            description=_clean_description(info.get("description")),
            category=_first_category(info),
            type_="openapi",
            website=_provider_url(info, provider),
            documentation=origin_url if origin_url and origin_url.startswith("http") else None,
            spec=spec_url,
            terms=info.get("termsOfService"),
            access_model="unknown",
            pricing_model="unknown",
            license_name=licence.get("name"),
            license_url=licence.get("url"),
            license_basis="upstream_catalog" if licence.get("name") else None,
            tags=[c for c in (info.get("x-apisguru-categories") or []) if isinstance(c, str) and len(c) > 2],
            update_frequency=update_frequency,
            provider_name=provider,
            source=SOURCE,
            source_url=f"https://apis.guru/browse-apis/",
            source_license=SOURCE_LICENSE,
            upstream_id=f"{provider}@{preferred}",
            source_version=version,
            notes=None,
        )
        rec["provider"]["id"] = provider.split(":", 1)[0]
        rec["provider"]["domain"] = (provider.split(":", 1)[0]
                                     if "." in provider.split(":", 1)[0]
                                     else rec["provider"].get("domain"))
        records.append(rec)
    return records


def parse_file(path: Path, version: str | None = None) -> list[dict[str, Any]]:
    return parse(json.loads(path.read_text(encoding="utf-8")), version)
