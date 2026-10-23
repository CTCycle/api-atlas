"""Record construction, normalisation and merging rules."""

from __future__ import annotations

import copy
import datetime as dt
from typing import Any
from urllib.parse import urlsplit

from . import ids, schema

TODAY = dt.date.today().isoformat()

EMPTY_TOKENS = (None, "", "unknown")
LEVEL_RANK = {"imported": 1, "curated": 2}
DATASET_EXTENSIONS = {
    "csv": "csv", "tsv": "tsv", "json": "json", "jsonl": "jsonl",
    "ndjson": "jsonl", "geojson": "geojson", "parquet": "parquet",
    "xlsx": "xlsx", "xls": "xls", "zip": "zip", "gz": "gzip",
    "xml": "xml", "shp": "shapefile", "tif": "geotiff", "tiff": "geotiff",
    "nc": "netcdf", "h5": "hdf5", "hdf5": "hdf5", "sqlite": "sqlite",
    "db": "sqlite", "pdf": "pdf", "rdf": "rdf", "ttl": "turtle",
    "arrow": "arrow", "feather": "feather", "avro": "avro",
}


def blank_record() -> dict[str, Any]:
    return {
        "id": "",
        "kind": "api",
        "name": "",
        "description": None,
        "category": "unknown",
        "tags": [],
        "type": "unknown",
        "provider": {"id": "", "name": "", "domain": None},
        "urls": {"website": None, "documentation": None, "spec": None,
                 "signup": None, "terms": None},
        "access": {"model": "unknown", "notes": None},
        "technical": {"https": None, "cors": "unknown", "auth_schemes": []},
        "pricing": {"model": "unknown", "free_tier_indicated": None,
                    "free_tier_limits": None, "basis": None, "notes": None},
        "license": {"name": None, "spdx": None, "url": None,
                    "commercial_use": "unknown", "attribution_required": None,
                    "basis": None, "notes": None},
        "coverage": {"geographic": None, "temporal": None},
        "formats": [],
        "update_frequency": "unknown",
        "status": "unverified",
        "verification": {"last_verified": None, "last_checked": None,
                         "method": "upstream_import", "confidence": "imported",
                         "http_status": None, "notes": None},
        "curation": {"level": "imported", "updated": TODAY},
        "provenance": [],
    }


def infer_formats(url: str | None) -> list[str]:
    if not url:
        return []
    path = urlsplit(url).path.lower()
    if "." not in path:
        return []
    ext = path.rsplit(".", 1)[-1]
    fmt = DATASET_EXTENSIONS.get(ext)
    return [fmt] if fmt else []


def _is_empty(value: Any) -> bool:
    return value is None or value == "" or value == "unknown" or value == [] or value == {}


def new_record(
    *,
    kind: str,
    name: str,
    source: str,
    website: str | None = None,
    documentation: str | None = None,
    spec: str | None = None,
    signup: str | None = None,
    terms: str | None = None,
    description: str | None = None,
    category: str = "unknown",
    type_: str | None = None,
    provider_name: str | None = None,
    domain: str | None = None,
    access_model: str = "unknown",
    access_notes: str | None = None,
    auth_schemes: list[str] | None = None,
    pricing_model: str = "unknown",
    pricing_basis: str | None = None,
    free_tier_indicated: bool | None = None,
    free_tier_limits: str | None = None,
    license_name: str | None = None,
    license_spdx: str | None = None,
    license_url: str | None = None,
    commercial_use: str = "unknown",
    attribution_required: bool | None = None,
    license_basis: str | None = None,
    geographic: str | None = None,
    temporal: str | None = None,
    formats: list[str] | None = None,
    update_frequency: str = "unknown",
    tags: list[str] | None = None,
    https: bool | None = None,
    cors: str = "unknown",
    source_url: str | None = None,
    source_license: str | None = None,
    upstream_id: str | None = None,
    source_version: str | None = None,
    level: str = "imported",
    notes: str | None = None,
    status: str = "unverified",
    confidence: str = "imported",
    method: str = "upstream_import",
) -> dict[str, Any]:
    """Build a normalised record. Unknown values stay unknown."""
    rec = blank_record()
    rec["kind"] = kind
    rec["name"] = (name or "").strip()
    rec["description"] = (description or "").strip() or None
    rec["category"] = category if category in schema.categories() else "unknown"
    rec["type"] = type_ or ("rest" if kind == "api" else "dataset")
    rec["urls"] = {
        "website": ids.normalize_url(website),
        "documentation": ids.normalize_url(documentation),
        "spec": ids.normalize_url(spec),
        "signup": ids.normalize_url(signup),
        "terms": ids.normalize_url(terms),
    }
    provider_id, provider_domain = ids.provider_identity(
        ids.normalize_url(website) or ids.normalize_url(documentation) or ids.normalize_url(spec),
        fallback_name=provider_name or name,
    )
    rec["provider"] = {
        "id": domain or provider_id,
        "name": (provider_name or name or "").strip(),
        "domain": provider_domain,
    }
    rec["access"] = {"model": access_model, "notes": access_notes}
    rec["technical"] = {"https": https, "cors": cors, "auth_schemes": auth_schemes or []}
    rec["pricing"] = {
        "model": pricing_model,
        "free_tier_indicated": free_tier_indicated,
        "free_tier_limits": free_tier_limits,
        "basis": pricing_basis,
        "notes": None,
    }
    rec["license"] = {
        "name": license_name,
        "spdx": license_spdx,
        "url": ids.normalize_url(license_url),
        "commercial_use": commercial_use,
        "attribution_required": attribution_required,
        "basis": license_basis,
        "notes": None,
    }
    rec["coverage"] = {"geographic": geographic, "temporal": temporal}
    derived = infer_formats(rec["urls"]["website"] or rec["urls"]["documentation"])
    rec["formats"] = sorted({*(formats or []), *derived})
    rec["update_frequency"] = update_frequency
    rec["tags"] = sorted(set(tags or []))
    rec["status"] = status
    rec["verification"] = {
        "last_verified": None,
        "last_checked": None,
        "method": method,
        "confidence": confidence,
        "http_status": None,
        "notes": None,
    }
    rec["curation"] = {"level": level, "updated": TODAY}
    rec["provenance"] = [{
        "source": source,
        "source_url": ids.normalize_url(source_url),
        "source_license": source_license,
        "upstream_id": upstream_id,
        "imported_at": TODAY,
        "source_version": source_version,
    }]
    rec["notes"] = notes
    rec["id"] = f"{rec['provider']['id']}/{ids.slugify(rec['name'])}"
    return normalize_record(rec)


def normalize_record(rec: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(rec)
    base = blank_record()

    def fill(node: dict[str, Any], defaults: dict[str, Any]) -> None:
        for key, value in defaults.items():
            if key not in node:
                node[key] = copy.deepcopy(value)
            elif isinstance(value, dict) and isinstance(node.get(key), dict):
                fill(node[key], value)

    fill(out, base)
    for key in ("website", "documentation", "spec", "signup", "terms"):
        out["urls"][key] = ids.normalize_url(out["urls"].get(key))
    if not out.get("provider", {}).get("id"):
        provider_id, provider_domain = ids.provider_identity(
            out["urls"].get("website") or out["urls"].get("documentation"),
            fallback_name=out.get("name"),
        )
        out["provider"] = {"id": provider_id, "name": out.get("name") or provider_id,
                           "domain": provider_domain}
    if out["category"] not in schema.categories():
        out["category"] = "unknown"
    if not out.get("id"):
        out["id"] = f"{out['provider']['id']}/{ids.slugify(out.get('name') or 'entry')}"
    out["tags"] = sorted({t for t in out.get("tags", []) if t})
    out["formats"] = sorted({f for f in out.get("formats", []) if f})
    return out


def apply_provider_policy(rec: dict[str, Any], root: str | None = None) -> dict[str, Any]:
    """Apply published provider licensing when the entry itself has none."""
    domain = (rec.get("provider") or {}).get("domain") or ""
    rule = schema.policy_for(domain, root)
    if not rule:
        return rec
    lic_rule = rule.get("license") or {}
    lic = rec.setdefault("license", {})
    if _is_empty(lic.get("name")) and lic_rule:
        lic["name"] = lic_rule.get("name")
        lic["spdx"] = lic_rule.get("spdx")
        lic["url"] = ids.normalize_url(lic_rule.get("url"))
        lic["commercial_use"] = lic_rule.get("commercial_use", "unknown")
        lic["attribution_required"] = lic_rule.get("attribution_required")
        lic["basis"] = "provider_policy"
        if lic_rule.get("notes"):
            lic["notes"] = lic_rule["notes"]
    cov_rule = rule.get("coverage") or {}
    cov = rec.setdefault("coverage", {})
    for key in ("geographic", "temporal"):
        if _is_empty(cov.get(key)) and cov_rule.get(key):
            cov[key] = cov_rule[key]
    return rec


def _merge_lists(old: list[Any], new: list[Any], path: str) -> list[Any]:
    if path == "provenance":
        seen = {(p.get("source"), p.get("upstream_id")) for p in old}
        merged = list(old)
        for item in new:
            key = (item.get("source"), item.get("upstream_id"))
            if key not in seen:
                merged.append(item)
                seen.add(key)
        return merged
    if path == "flags":
        return old + [f for f in new if f not in old]
    return sorted({*old, *new}) if path in ("tags", "formats", "aliases") else list(old)


SKIP_ON_VERIFIED = {"verification", "status"}


def merge_into(existing: dict[str, Any], incoming: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Merge an incoming record into an existing one.

    Rules, in order of importance:
    * verification and status are owned by the verifier, imports never reset them
    * curated fields are never overwritten by imported ones
    * curated data overwrites imported data, and disagreements are recorded
    * among imported data, non-empty values win and longer descriptions replace terse ones
    """
    existing_level = (existing.get("curation") or {}).get("level", "imported")
    incoming_level = (incoming.get("curation") or {}).get("level", "imported")
    verify_state = (existing.get("verification") or {}).get("method", "none")
    verified_before = verify_state in ("http_head", "manual_review")
    before = copy.deepcopy(existing)
    out = copy.deepcopy(existing)

    for key, new_value in incoming.items():
        if key in ("id", "curation"):
            continue
        if key in SKIP_ON_VERIFIED and verified_before:
            continue
        if key in ("provenance", "tags", "formats", "aliases", "flags") and isinstance(new_value, list):
            old_list = out.get(key) or []
            out[key] = _merge_lists(old_list, new_value, key)
            continue
        old_value = out.get(key)
        if isinstance(new_value, dict) and isinstance(old_value, dict):
            out[key] = _merge_dict(old_value, new_value, key, existing_level, incoming_level, out)
            continue
        if _is_empty(new_value):
            continue
        if _is_empty(old_value):
            out[key] = new_value
            continue
        if new_value == old_value:
            continue
        if existing_level == "curated" and incoming_level == "imported":
            continue
        take_new = incoming_level == "curated" and existing_level != "curated"
        if key == "description" and isinstance(new_value, str) and isinstance(old_value, str):
            take_new = len(new_value) > len(old_value) + 20
        if take_new:
            if incoming_level == "curated":
                conflicts = out.setdefault("conflicts", [])
                conflicts.append({
                    "field": key,
                    "kept": new_value,
                    "discarded": old_value,
                    "discarded_source": _source_of(before),
                })
            out[key] = new_value

    if incoming_level == "curated" and existing_level != "curated":
        out["curation"] = {"level": "curated", "updated": TODAY}
    elif existing_level == "curated":
        out["curation"] = {"level": "curated",
                           "updated": (before.get("curation") or {}).get("updated") or TODAY}
    else:
        out["curation"] = {"level": "imported", "updated": TODAY}

    status = "unchanged" if out == before else "merged"
    return normalize_record(out), status


def _merge_dict(old: dict[str, Any], new: dict[str, Any], path: str,
                existing_level: str, incoming_level: str,
                parent: dict[str, Any]) -> dict[str, Any]:
    result = dict(old)
    for key, new_value in new.items():
        full = f"{path}.{key}"
        old_value = result.get(key)
        if isinstance(new_value, dict) and isinstance(old_value, dict):
            result[key] = _merge_dict(old_value, new_value, full, existing_level, incoming_level, parent)
            continue
        if isinstance(new_value, list) and isinstance(old_value, list):
            result[key] = _merge_lists(old_value, new_value, full)
            continue
        if _is_empty(new_value):
            continue
        if _is_empty(old_value):
            result[key] = new_value
            continue
        if new_value == old_value:
            continue
        if existing_level == "curated" and incoming_level == "imported":
            continue
        if incoming_level == "curated" and existing_level != "curated":
            parent.setdefault("conflicts", []).append({
                "field": full, "kept": new_value, "discarded": old_value,
                "discarded_source": _source_of(parent),
            })
            result[key] = new_value
    return result


def _source_of(rec: dict[str, Any]) -> str | None:
    prov = rec.get("provenance") or []
    if not prov:
        return None
    return prov[-1].get("source")
