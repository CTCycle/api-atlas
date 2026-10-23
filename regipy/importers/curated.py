"""Importer for locally curated seed entries (curation/seeds/*.yaml).

Curated entries are the highest trust tier in the catalog: a human (or an agent
acting as editor) has looked at the provider's own documentation. The seed file
format is documented in docs/maintenance.md; every field is optional except
name, kind, category and provider, and anything omitted stays unknown.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import yaml

from .. import models, schema
from ..models import new_record

SOURCE = "curated"
SOURCE_URL = "https://github.com/CTCycle/api-dataset-registry"
SOURCE_LICENSE = "CC-BY-4.0"


def parse_file(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    records: list[dict[str, Any]] = []
    for raw in entries:
        name = (raw.get("name") or "").strip()
        if not name:
            continue
        verified_on = raw.get("verified_on")
        confidence = raw.get("confidence") or ("verified" if verified_on else "partial")
        method = "manual_review" if confidence in ("verified", "partial") else "none"
        rec = new_record(
            kind=raw.get("kind", "api"),
            name=name,
            description=raw.get("description"),
            category=raw.get("category", "unknown"),
            type_=raw.get("type"),
            provider_name=raw.get("provider_name") or name,
            domain=raw.get("provider"),
            website=raw.get("website"),
            documentation=raw.get("documentation"),
            spec=raw.get("spec"),
            signup=raw.get("signup"),
            terms=raw.get("terms") or raw.get("license_url"),
            access_model=raw.get("access", "unknown"),
            access_notes=raw.get("access_notes"),
            auth_schemes=raw.get("auth_schemes"),
            pricing_model=raw.get("pricing", "unknown"),
            pricing_basis=raw.get("pricing_basis"),
            free_tier_indicated=raw.get("free_tier_indicated"),
            free_tier_limits=raw.get("free_tier_limits"),
            license_name=raw.get("license"),
            license_spdx=raw.get("license_spdx"),
            license_url=raw.get("license_url"),
            commercial_use=raw.get("commercial_use", "unknown"),
            attribution_required=raw.get("attribution_required"),
            license_basis=raw.get("license_basis"),
            geographic=raw.get("geographic"),
            temporal=raw.get("temporal"),
            formats=raw.get("formats"),
            update_frequency=raw.get("update_frequency", "unknown"),
            tags=raw.get("tags"),
            https=raw.get("https"),
            cors=raw.get("cors", "unknown"),
            source=SOURCE,
            source_url=SOURCE_URL,
            source_license=SOURCE_LICENSE,
            upstream_id=str(path.name) + "#" + name,
            level="curated",
            notes=raw.get("notes"),
            status="active" if verified_on else "unverified",
            confidence=confidence,
            method=method,
        )
        if raw.get("provider"):
            rec["provider"]["id"] = str(raw["provider"]).lower()
            rec["provider"]["domain"] = str(raw["provider"]).lower()
        if verified_on:
            rec["verification"]["last_verified"] = verified_on
            rec["verification"]["last_checked"] = verified_on
        rec["curation"] = {"level": "curated", "updated": dt.date.today().isoformat()}
        models.apply_provider_policy(rec)
        records.append(rec)
    return records


def parse_dir(directory: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.yaml")):
        records.extend(parse_file(path))
    return records
