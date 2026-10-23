"""SQLite full text search index over the registry catalog."""

from __future__ import annotations

import datetime as dt
import json
import sqlite3
from pathlib import Path
from typing import Any

from . import schema

ENTRY_COLUMNS = (
    "id", "kind", "name", "description", "category", "type", "provider_id",
    "provider_name", "provider_domain", "website", "documentation", "access_model",
    "pricing_model", "free_tier_indicated", "free_tier_limits", "license_name",
    "license_spdx", "commercial_use", "update_frequency", "status", "confidence",
    "last_verified", "http_status", "json",
)

CREATE_ENTRIES = """
CREATE TABLE entries (
    id TEXT PRIMARY KEY,
    kind TEXT,
    name TEXT,
    description TEXT,
    category TEXT,
    type TEXT,
    provider_id TEXT,
    provider_name TEXT,
    provider_domain TEXT,
    website TEXT,
    documentation TEXT,
    access_model TEXT,
    pricing_model TEXT,
    free_tier_indicated INTEGER,
    free_tier_limits TEXT,
    license_name TEXT,
    license_spdx TEXT,
    commercial_use TEXT,
    update_frequency TEXT,
    status TEXT,
    confidence TEXT,
    last_verified TEXT,
    http_status INTEGER,
    json TEXT
)
"""

CREATE_FTS = """
CREATE VIRTUAL TABLE entries_fts USING fts5(
    id UNINDEXED,
    name,
    description,
    tags,
    provider_name,
    tokenize='porter unicode61'
)
"""


def _default_db_path(store: Any = None) -> Path:
    if store is not None and getattr(store, "root", None) is not None:
        return Path(store.root) / "data" / "registry.sqlite"
    return schema.repo_root() / "data" / "registry.sqlite"


def _resolve_db_path(db_path: Any = None, store: Any = None) -> Path:
    if db_path is None:
        return _default_db_path(store)
    return Path(db_path)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _record_fields(record: dict[str, Any]) -> tuple[Any, ...]:
    provider = record.get("provider") or {}
    urls = record.get("urls") or {}
    access = record.get("access") or {}
    pricing = record.get("pricing") or {}
    license_info = record.get("license") or {}
    verification = record.get("verification") or {}
    free_tier = pricing.get("free_tier_indicated")
    free_tier_int = 1 if free_tier is True else (0 if free_tier is False else None)
    return (
        record.get("id"),
        record.get("kind"),
        record.get("name"),
        record.get("description"),
        record.get("category"),
        record.get("type"),
        provider.get("id"),
        provider.get("name"),
        provider.get("domain"),
        urls.get("website"),
        urls.get("documentation"),
        access.get("model"),
        pricing.get("model"),
        free_tier_int,
        pricing.get("free_tier_limits"),
        license_info.get("name"),
        license_info.get("spdx"),
        license_info.get("commercial_use"),
        record.get("update_frequency"),
        record.get("status"),
        verification.get("confidence"),
        verification.get("last_verified"),
        verification.get("http_status"),
        json.dumps(record, ensure_ascii=False),
    )


def build_index(store: Any, db_path: Any = None) -> dict[str, Any]:
    """Build or rebuild the SQLite search index from *store*."""
    if not getattr(store, "loaded", False):
        if not getattr(store, "records", None):
            try:
                store.load()
            except Exception:
                pass
        else:
            store.loaded = True
    path = _resolve_db_path(db_path, store)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = _connect(path)
    try:
        conn.executescript("DROP TABLE IF EXISTS entries_fts; DROP TABLE IF EXISTS entries;")
        conn.execute(CREATE_ENTRIES)
        conn.execute(CREATE_FTS)
        records = list(store.all())
        for record in records:
            conn.execute(
                "INSERT INTO entries (" + ", ".join(ENTRY_COLUMNS) + ") VALUES ("
                + ", ".join("?" for _ in ENTRY_COLUMNS) + ")",
                _record_fields(record),
            )
            tags = record.get("tags") or []
            provider = record.get("provider") or {}
            conn.execute(
                "INSERT INTO entries_fts (id, name, description, tags, provider_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    record.get("id"),
                    record.get("name"),
                    record.get("description") or "",
                    " ".join(str(tag) for tag in tags),
                    provider.get("name") or "",
                ),
            )
        conn.commit()
    finally:
        conn.close()
    built_at = dt.datetime.now(dt.timezone.utc).isoformat()
    return {"entries": len(records), "path": str(path), "built_at": built_at}


def index_exists(db_path: Any = None) -> bool:
    path = Path(db_path) if db_path is not None else _default_db_path()
    if not path.is_file():
        return False
    try:
        conn = _connect(path)
        try:
            entries = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries'"
            ).fetchone()
            fts = conn.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='entries_fts'"
            ).fetchone()
            return bool(entries and fts)
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def index_age_hours(db_path: Any = None) -> float | None:
    path = Path(db_path) if db_path is not None else _default_db_path()
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
    except OSError:
        return None
    return (dt.datetime.now(dt.timezone.utc).timestamp() - mtime) / 3600.0


def ensure_index(store: Any = None, db_path: Any = None, max_age_hours: float = 24) -> str:
    path = _resolve_db_path(db_path, store)
    if store is None:
        from . import store as store_module

        store = store_module.Store()
        try:
            store.load()
        except Exception:
            pass
    age = index_age_hours(path)
    if not index_exists(path) or age is None or (max_age_hours is not None and age > max_age_hours):
        build_index(store, path)
    return str(path)


def _normalize_filter(value: Any) -> list[str] | None:
    if value is None:
        return None
    if isinstance(value, str):
        tokens = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        tokens = [str(part).strip() for part in value]
    else:
        tokens = [str(value).strip()]
    tokens = [token for token in tokens if token != ""]
    return tokens or None


def _split_include_exclude(tokens: list[str] | None) -> tuple[list[str], list[str]]:
    includes: list[str] = []
    excludes: list[str] = []
    if not tokens:
        return includes, excludes
    for token in tokens:
        if token.startswith("!"):
            remainder = token[1:].strip().lower()
            if remainder:
                excludes.append(remainder)
        else:
            includes.append(token.lower())
    return includes, excludes


def _scalar_ok(tokens: list[str] | None, actual: Any) -> bool:
    includes, excludes = _split_include_exclude(tokens)
    actual_text = "" if actual is None else str(actual).lower()
    if includes and actual_text not in includes:
        return False
    if excludes and actual_text in excludes:
        return False
    return True


def _provider_ok(tokens: list[str] | None, record: dict[str, Any]) -> bool:
    includes, excludes = _split_include_exclude(tokens)
    provider = record.get("provider") or {}
    values = [
        provider.get("id"),
        provider.get("name"),
        provider.get("domain"),
    ]
    lowers = [str(value).lower() for value in values if value is not None]
    if includes and not any(value in includes for value in lowers):
        return False
    if excludes and any(value in excludes for value in lowers):
        return False
    return True


def _data_format_ok(tokens: list[str] | None, record: dict[str, Any]) -> bool:
    includes, excludes = _split_include_exclude(tokens)
    formats = [str(item).lower() for item in (record.get("formats") or [])]
    if includes and not any(item in includes for item in formats):
        return False
    if excludes and any(item in excludes for item in formats):
        return False
    return True


def _free_tier_ok(free_tier: Any, record: dict[str, Any]) -> bool:
    if free_tier is None:
        return True
    indicated = (record.get("pricing") or {}).get("free_tier_indicated")
    if isinstance(free_tier, bool):
        wanted = free_tier
    else:
        text = str(free_tier).strip().lower()
        if text in ("true", "1", "yes"):
            wanted = True
        elif text in ("false", "0", "no"):
            wanted = False
        else:
            return True
    if wanted:
        return indicated is True or indicated == 1
    return indicated is False or indicated == 0


def _record_matches(record: dict[str, Any], filters: dict[str, Any]) -> bool:
    if not _scalar_ok(filters.get("category"), record.get("category")):
        return False
    if not _scalar_ok(filters.get("kind"), record.get("kind")):
        return False
    if not _scalar_ok(filters.get("pricing"), (record.get("pricing") or {}).get("model")):
        return False
    if not _scalar_ok(filters.get("access"), (record.get("access") or {}).get("model")):
        return False
    if not _scalar_ok(filters.get("commercial"), (record.get("license") or {}).get("commercial_use")):
        return False
    if not _scalar_ok(filters.get("status"), record.get("status")):
        return False
    if not _scalar_ok(filters.get("confidence"), (record.get("verification") or {}).get("confidence")):
        return False
    if not _scalar_ok(filters.get("update_frequency"), record.get("update_frequency")):
        return False
    if not _provider_ok(filters.get("provider"), record):
        return False
    if not _scalar_ok(filters.get("license_spdx"), (record.get("license") or {}).get("spdx")):
        return False
    if not _free_tier_ok(filters.get("free_tier"), record):
        return False
    data_format = filters.get("data_format")
    if data_format is not None and not _data_format_ok(_normalize_filter(data_format), record):
        return False
    verified_since = filters.get("verified_since")
    if verified_since is not None:
        actual = (record.get("verification") or {}).get("last_verified")
        if actual is None or str(actual) < str(verified_since):
            return False
    return True


def _sort_verified(records: list[dict[str, Any]]) -> None:
    records.sort(key=lambda record: (record.get("name") or "").lower())
    records.sort(
        key=lambda record: (record.get("verification") or {}).get("last_verified") or "",
        reverse=True,
    )
    records.sort(
        key=lambda record: (record.get("verification") or {}).get("last_verified") is None
    )


def _query_records(
    db_path: Any = None,
    *,
    text: Any = None,
    category: Any = None,
    kind: Any = None,
    pricing: Any = None,
    access: Any = None,
    commercial: Any = None,
    status: Any = None,
    confidence: Any = None,
    data_format: Any = None,
    update_frequency: Any = None,
    verified_since: Any = None,
    provider: Any = None,
    license_spdx: Any = None,
    free_tier: Any = None,
    limit: int | None = None,
    offset: int = 0,
    order: str = "relevance",
) -> list[dict[str, Any]]:
    path = _resolve_db_path(db_path)
    filters = {
        "category": _normalize_filter(category),
        "kind": _normalize_filter(kind),
        "pricing": _normalize_filter(pricing),
        "access": _normalize_filter(access),
        "commercial": _normalize_filter(commercial),
        "status": _normalize_filter(status),
        "confidence": _normalize_filter(confidence),
        "update_frequency": _normalize_filter(update_frequency),
        "provider": _normalize_filter(provider),
        "license_spdx": _normalize_filter(license_spdx),
        "free_tier": free_tier,
        "data_format": data_format,
        "verified_since": verified_since,
    }
    text_value = None if text is None else str(text).strip()
    if text_value == "":
        text_value = None

    conn = _connect(path)
    try:
        scores: dict[str, float] = {}
        if text_value is None:
            rows = conn.execute("SELECT * FROM entries").fetchall()
        else:
            try:
                id_rows = conn.execute(
                    "SELECT id FROM entries_fts WHERE entries_fts MATCH ?",
                    (text_value,),
                ).fetchall()
                ids = [row["id"] for row in id_rows]
                score_rows = conn.execute(
                    "SELECT id, bm25(entries_fts) AS score FROM entries_fts WHERE entries_fts MATCH ?",
                    (text_value,),
                ).fetchall()
                scores = {row["id"]: row["score"] for row in score_rows}
                if ids:
                    placeholders = ", ".join("?" for _ in ids)
                    rows = conn.execute(
                        "SELECT * FROM entries WHERE id IN (" + placeholders + ")",
                        ids,
                    ).fetchall()
                else:
                    rows = []
            except sqlite3.OperationalError:
                like = "%" + text_value + "%"
                rows = conn.execute(
                    "SELECT * FROM entries WHERE "
                    "LOWER(COALESCE(name, '')) LIKE LOWER(?) OR "
                    "LOWER(COALESCE(description, '')) LIKE LOWER(?) OR "
                    "LOWER(COALESCE(json, '')) LIKE LOWER(?) OR "
                    "LOWER(COALESCE(provider_name, '')) LIKE LOWER(?)",
                    (like, like, like, like),
                ).fetchall()
                scores = {}
    finally:
        conn.close()

    candidates: list[dict[str, Any]] = []
    for row in rows:
        try:
            record = json.loads(row["json"])
        except (TypeError, json.JSONDecodeError):
            continue
        if not _record_matches(record, filters):
            continue
        candidates.append(record)

    if order == "name":
        candidates.sort(key=lambda record: (record.get("name") or "").lower())
    elif order == "verified":
        _sort_verified(candidates)
    elif order == "recent":
        _sort_verified(candidates)
    else:
        if text_value is not None and scores:
            candidates.sort(key=lambda record: (record.get("name") or "").lower())
            candidates.sort(key=lambda record: scores.get(record.get("id"), 0.0))
        else:
            candidates.sort(key=lambda record: (record.get("name") or "").lower())

    if offset:
        candidates = candidates[offset:]
    if limit is not None:
        candidates = candidates[:limit]
    return candidates


def query(
    db_path: Any = None,
    *,
    text: Any = None,
    category: Any = None,
    kind: Any = None,
    pricing: Any = None,
    access: Any = None,
    commercial: Any = None,
    status: Any = None,
    confidence: Any = None,
    data_format: Any = None,
    update_frequency: Any = None,
    verified_since: Any = None,
    provider: Any = None,
    license_spdx: Any = None,
    free_tier: Any = None,
    limit: int | None = None,
    offset: int = 0,
    order: str = "relevance",
) -> list[dict[str, Any]]:
    return _query_records(
        db_path,
        text=text,
        category=category,
        kind=kind,
        pricing=pricing,
        access=access,
        commercial=commercial,
        status=status,
        confidence=confidence,
        data_format=data_format,
        update_frequency=update_frequency,
        verified_since=verified_since,
        provider=provider,
        license_spdx=license_spdx,
        free_tier=free_tier,
        limit=limit,
        offset=offset,
        order=order,
    )


def count(db_path: Any = None, **same_filters: Any) -> int:
    filters = dict(same_filters)
    filters.pop("limit", None)
    filters.pop("offset", None)
    filters.pop("order", None)
    return len(_query_records(db_path, **filters))


def facets(db_path: Any = None) -> dict[str, dict[str, int]]:
    path = _resolve_db_path(db_path)
    conn = _connect(path)
    try:
        rows = conn.execute("SELECT * FROM entries").fetchall()
    finally:
        conn.close()
    result: dict[str, dict[str, int]] = {
        "category": {},
        "pricing": {},
        "access": {},
        "confidence": {},
        "commercial_use": {},
    }
    for row in rows:
        category = row["category"] if row["category"] is not None else "unknown"
        pricing = row["pricing_model"] if row["pricing_model"] is not None else "unknown"
        access = row["access_model"] if row["access_model"] is not None else "unknown"
        confidence = row["confidence"] if row["confidence"] is not None else "unknown"
        commercial = row["commercial_use"] if row["commercial_use"] is not None else "unknown"
        result["category"][category] = result["category"].get(category, 0) + 1
        result["pricing"][pricing] = result["pricing"].get(pricing, 0) + 1
        result["access"][access] = result["access"].get(access, 0) + 1
        result["confidence"][confidence] = result["confidence"].get(confidence, 0) + 1
        result["commercial_use"][commercial] = result["commercial_use"].get(commercial, 0) + 1
    for key in result:
        result[key] = dict(sorted(result[key].items()))
    return result
