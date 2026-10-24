"""HTTP link checking for registry entries.

Verification semantics: three confidence tiers exist. ``imported`` means the
record was never checked. ``partial`` means it was HTTP checked or carries
editorial metadata only. ``verified`` means it was checked and key metadata
was confirmed from official documentation. A link check can only ever produce
``partial``; it never promotes a record to ``verified``.

Status values are ``active``, ``deprecated``, ``unavailable`` and
``unverified``. ``verification.last_checked`` records any attempt,
``verification.last_verified`` records only successful checks and
``verification.http_status`` stores the HTTP status code.
"""

from __future__ import annotations

import datetime as dt
import random
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable
from urllib.parse import urlsplit

USER_AGENT = "api-atlas-linkcheck/1.0 (+https://github.com/CTCycle/api-atlas)"

RETRY_STATUSES = {403, 405, 406, 501}
GATED_STATUSES = {401, 403, 429, 451}
BROKEN_STATUSES = {404, 410}


def _today(value: str | None) -> str:
    if value:
        return value
    return dt.date.today().isoformat()


def _parse_date(value: str | None) -> dt.date | None:
    if not value:
        return None
    try:
        return dt.date.fromisoformat(value)
    except ValueError:
        return None


def check_url(url: str, *, timeout: float = 15.0,
              user_agent: str = USER_AGENT) -> dict[str, Any]:
    """Perform a polite HTTP check of ``url``.

    Returns a dict with keys ``ok``, ``status``, ``error``, ``elapsed_ms``
    and ``method``.
    """
    start = time.monotonic()
    status: int | None = None
    error: str | None = None
    method = "head"
    ctx = ssl.create_default_context()

    def _request(req_method: str, extra_headers: dict[str, str] | None = None) -> int:
        headers = {"User-Agent": user_agent, "Accept": "*/*"}
        if extra_headers:
            headers.update(extra_headers)
        req = urllib.request.Request(url, method=req_method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                return int(resp.getcode())
        except urllib.error.HTTPError as exc:
            return int(exc.code)
        except Exception:
            raise

    # HEAD first.
    try:
        status = _request("HEAD")
        method = "head"
    except Exception as exc:  # noqa: BLE001
        # Convert to a retryable failure below.
        status = None
        error = str(exc)

    # Retry with GET when the server dislikes HEAD.
    if status is None or status in RETRY_STATUSES:
        if status in RETRY_STATUSES or error is not None:
            # Only retry on retryable HTTP statuses or transport errors from
            # HEAD. Transport errors are not retried with GET to avoid hammering.
            if status in RETRY_STATUSES:
                try:
                    method = "get"
                    status = _request("GET", {"Range": "bytes=0-1024"})
                    error = None
                except Exception as exc:  # noqa: BLE001
                    status = None
                    error = str(exc)
            # else: keep the transport error

    # Classify.
    if status is not None:
        ok = 200 <= status < 400
        if ok:
            error = None
        elif error is None:
            error = f"HTTP {status}"
    else:
        ok = False
        if error is None:
            error = "unknown error"

    elapsed_ms = int(round((time.monotonic() - start) * 1000))
    return {
        "ok": bool(ok),
        "status": status,
        "error": error,
        "elapsed_ms": elapsed_ms,
        "method": method,
    }


def _call_checker(checker: Callable[..., dict[str, Any]], url: str,
                  timeout: float) -> dict[str, Any]:
    for kwargs in (
        {"timeout": timeout, "user_agent": USER_AGENT},
        {"timeout": timeout},
        {},
    ):
        try:
            return checker(url, **kwargs)
        except TypeError:
            continue
    return checker(url)


def _age_days(today: str, last_checked: str | None) -> int | None:
    t = _parse_date(today)
    lc = _parse_date(last_checked)
    if t is None or lc is None:
        return None
    return (t - lc).days


def linkcheck(
    store: Any,
    *,
    limit: int | None = None,
    kind: str | None = None,
    category: str | None = None,
    ids: list[str] | None = None,
    workers: int = 8,
    timeout: float = 15.0,
    dry_run: bool = False,
    force: bool = False,
    today: str | None = None,
    max_age_days: int | None = 30,
    checker: Callable[..., dict[str, Any]] = check_url,
) -> dict[str, Any]:
    """Check website URLs in ``store`` and update verification metadata."""
    today_str = _today(today)
    id_set = set(ids) if ids else None

    selected: list[Any] = []
    for rec in store.all():
        if not (rec.get("urls") or {}).get("website"):
            continue
        if kind is not None and rec.get("kind") != kind:
            continue
        if category is not None and rec.get("category") != category:
            continue
        if id_set is not None and rec.get("id") not in id_set:
            continue
        if not force:
            ver = rec.get("verification") or {}
            last_checked = ver.get("last_checked")
            if last_checked == today_str:
                continue
            if max_age_days is not None and last_checked:
                age = _age_days(today_str, last_checked)
                if age is not None and age <= max_age_days:
                    continue
        selected.append(rec)
        if limit is not None and len(selected) >= limit:
            break

    checked = 0
    ok_count = 0
    broken = 0
    gated = 0
    errors = 0
    updated = 0
    results: list[dict[str, Any]] = []

    workers = max(1, min(int(workers or 1), 8))

    def _process(rec: dict[str, Any]) -> dict[str, Any]:
        url = (rec.get("urls") or {}).get("website")
        # Politeness jitter.
        time.sleep(0.15 + random.uniform(0.0, 0.05))
        return _call_checker(checker, url, timeout)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        future_by_rec = {pool.submit(_process, rec): rec for rec in selected}
        future_for_rec = {id(r): f for f, r in future_by_rec.items()}
        for rec in selected:
            future = future_for_rec[id(rec)]
            try:
                result = future.result()
            except Exception as exc:  # noqa: BLE001
                result = {
                    "ok": False, "status": None, "error": str(exc),
                    "elapsed_ms": 0, "method": "head",
                }
            checked += 1
            rid = rec.get("id")
            url = (rec.get("urls") or {}).get("website")
            status = result.get("status")
            is_ok = bool(result.get("ok"))
            err = result.get("error")

            action = "checked"
            if not dry_run:
                ver = rec.setdefault("verification", {})
                ver["last_checked"] = today_str
                if status is not None:
                    ver["http_status"] = status
                if is_ok:
                    ok_count += 1
                    if rec.get("status") != "deprecated":
                        rec["status"] = "active"
                    ver["last_verified"] = today_str
                    ver["method"] = "http_head"
                    if ver.get("confidence") == "imported":
                        ver["confidence"] = "partial"
                    ver["notes"] = None
                    action = "updated"
                    updated += 1
                elif status in BROKEN_STATUSES:
                    broken += 1
                    rec["status"] = "unavailable"
                    ver["notes"] = err or f"HTTP {status}"
                    ver["method"] = "http_head"
                    action = "updated"
                    updated += 1
                elif status in GATED_STATUSES:
                    gated += 1
                    if rec.get("status") == "active":
                        rec["status"] = "active"
                    else:
                        rec["status"] = "unverified"
                    ver["notes"] = err or f"HTTP {status}"
                    ver["method"] = "http_head"
                    action = "updated"
                    updated += 1
                else:
                    errors += 1
                    ver["notes"] = err
                    if status is not None:
                        ver["method"] = "http_head"
                    action = "updated" if err else "error"
                    # status untouched
                    updated += 1
                try:
                    store.dirty.add(rid)
                except Exception:
                    pass
            else:
                # Dry run: classify counts but do not mutate.
                if is_ok:
                    ok_count += 1
                elif status in BROKEN_STATUSES:
                    broken += 1
                elif status in GATED_STATUSES:
                    gated += 1
                else:
                    errors += 1
                action = "dry_run"

            results.append({
                "id": rid,
                "url": url,
                "status": status,
                "ok": is_ok,
                "error": err,
                "action": action,
            })

    # Tidy gated status rule: ensure active stays active, non-active -> unverified.
    # (Already handled above.)

    return {
        "checked": checked,
        "ok": ok_count,
        "broken": broken,
        "gated": gated,
        "errors": errors,
        "updated": updated if not dry_run else 0,
        "results": results,
    }
