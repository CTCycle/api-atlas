"""Schema, taxonomy and provider policy loading plus semantic validation."""

from __future__ import annotations

import datetime as dt
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent

API_TYPES = {"rest", "graphql", "openapi", "feed", "unknown"}
DATASET_TYPES = {"dataset", "download", "database", "portal", "unknown"}

# Fields whose absence of information must be expressed as "unknown" rather
# than a guessed value. Used by the validator to catch accidental invention.
EVIDENCE_FIELDS = ("license.commercial_use",)


def repo_root(start: Path | None = None) -> Path:
    env = Path(start or Path.cwd())
    for candidate in [env, *env.parents]:
        if (candidate / "schema" / "entry.schema.json").exists():
            return candidate
    return ROOT


@lru_cache(maxsize=4)
def load_schema(root: str | None = None) -> dict[str, Any]:
    base = Path(root) if root else repo_root()
    return json.loads((base / "schema" / "entry.schema.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_taxonomy(root: str | None = None) -> dict[str, Any]:
    base = Path(root) if root else repo_root()
    return yaml.safe_load((base / "schema" / "taxonomy.yaml").read_text(encoding="utf-8"))


@lru_cache(maxsize=4)
def load_policies(root: str | None = None) -> list[dict[str, Any]]:
    base = Path(root) if root else repo_root()
    data = yaml.safe_load((base / "schema" / "provider-policies.yaml").read_text(encoding="utf-8"))
    return data.get("rules", [])


def categories(root: str | None = None) -> dict[str, dict[str, str]]:
    return load_taxonomy(root)["categories"]


def map_category(block: str, upstream: str | None, root: str | None = None) -> str:
    mapping = load_taxonomy(root).get(block, {})
    if not upstream:
        return "unknown"
    if upstream in mapping:
        return mapping[upstream]
    lowered = {k.lower(): v for k, v in mapping.items()}
    return lowered.get(upstream.lower(), "unknown")


def category_for_provider(domain: str | None, root: str | None = None) -> str | None:
    """Editorial classification used only when the upstream catalog has none."""
    if not domain:
        return None
    host = domain.lower()
    mapping = load_taxonomy(root).get("provider_categories") or {}
    best: tuple[int, str] | None = None
    for match, category in mapping.items():
        m = match.lower()
        if host == m or host.endswith("." + m):
            score = len(m)
            if best is None or score > best[0]:
                best = (score, category)
    return best[1] if best else None


def policy_for(domain: str | None, root: str | None = None) -> dict[str, Any] | None:
    if not domain:
        return None
    host = domain.lower()
    best: tuple[int, dict[str, Any]] | None = None
    for rule in load_policies(root):
        for match in rule.get("match", []):
            m = match.lower()
            if host == m or host.endswith("." + m):
                score = len(m)
                if best is None or score > best[0]:
                    best = (score, rule)
    return best[1] if best else None


def _iter_leaf_paths(obj: Any, prefix: str = ""):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from _iter_leaf_paths(value, f"{prefix}.{key}" if prefix else key)
    else:
        yield prefix


def get_path(record: dict[str, Any], path: str) -> Any:
    node: Any = record
    for part in path.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node


def set_path(record: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    node = record
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def validate_record(record: dict[str, Any], validator=None, root: str | None = None) -> list[str]:
    """Return a list of human readable problems. Empty list means valid."""
    errors: list[str] = []
    if validator is None:
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(load_schema(root))
    for err in sorted(validator.iter_errors(record), key=lambda e: list(e.path)):
        location = ".".join(str(p) for p in err.path) or "<root>"
        errors.append(f"{location}: {err.message}")

    cat = record.get("category")
    cats = categories(root)
    if cat and cat not in cats:
        errors.append(f"category: '{cat}' is not in schema/taxonomy.yaml")

    kind = record.get("kind")
    etype = record.get("type")
    if kind == "api" and etype in DATASET_TYPES and etype != "unknown":
        errors.append(f"type: '{etype}' is not valid for kind=api")
    if kind == "dataset" and etype in API_TYPES and etype != "unknown":
        errors.append(f"type: '{etype}' is not valid for kind=dataset")

    urls = record.get("urls") or {}
    for name, value in urls.items():
        if value and not re.match(r"^https?://", value):
            errors.append(f"urls.{name}: must be an absolute http(s) URL")

    lic = record.get("license") or {}
    if lic.get("commercial_use") not in (None, "unknown") and not lic.get("name"):
        errors.append("license.commercial_use: needs license.name as evidence, otherwise leave it 'unknown'")

    pricing = record.get("pricing") or {}
    if pricing.get("free_tier_indicated") is True and pricing.get("model") == "free" and pricing.get("free_tier_limits"):
        errors.append("pricing: model='free' should not carry paid tier limits")

    verification = record.get("verification") or {}
    for key in ("last_verified", "last_checked"):
        value = verification.get(key)
        if value:
            try:
                parsed = dt.date.fromisoformat(value)
            except ValueError:
                errors.append(f"verification.{key}: not an ISO date")
                continue
            if parsed > dt.date.today():
                errors.append(f"verification.{key}: date is in the future")

    if not record.get("provenance"):
        errors.append("provenance: at least one source record is required")

    return errors


def build_validator(root: str | None = None):
    from jsonschema import Draft202012Validator
    return Draft202012Validator(load_schema(root))
