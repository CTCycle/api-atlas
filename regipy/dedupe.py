"""Duplicate detection and merging for registry entries."""

from __future__ import annotations

import copy
from typing import Any
from urllib.parse import urlsplit

from . import ids, models

LEVEL_RANK = {"imported": 1, "curated": 2}


def _tokens(value: str) -> set[str]:
    return set((ids.normalize_name_for_match(value) or "").split())


def name_similarity(a: str, b: str) -> float:
    """Token Jaccard similarity on normalised names."""
    ta = _tokens(a)
    tb = _tokens(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    if union == 0:
        return 0.0
    return inter / union


def _website(rec: dict[str, Any]) -> str | None:
    return (rec.get("urls") or {}).get("website")


def _provider_domain(rec: dict[str, Any]) -> str | None:
    prov = rec.get("provider") or {}
    return prov.get("domain") or prov.get("id")


def _path_tokens(url: str | None) -> set[str]:
    if not url:
        return set()
    path = urlsplit(url).path.strip("/")
    if not path:
        return set()
    return {seg for seg in path.split("/") if seg}


def pair_score(rec_a: dict[str, Any], rec_b: dict[str, Any]) -> float:
    """Combine name similarity with URL path overlap when both have websites."""
    score = name_similarity(rec_a.get("name") or "", rec_b.get("name") or "")
    wa = _website(rec_a)
    wb = _website(rec_b)
    if wa and wb:
        pa = _path_tokens(wa)
        pb = _path_tokens(wb)
        if pa or pb:
            union = pa | pb
            overlap = (len(pa & pb) / len(union)) if union else 0.0
            score = min(1.0, score + 0.15 * overlap)
    return float(score)


def _curated_rank(rec: dict[str, Any]) -> int:
    level = (rec.get("curation") or {}).get("level", "imported")
    return LEVEL_RANK.get(level, 0)


def _populated_count(rec: dict[str, Any]) -> int:
    count = 0

    def walk(value: Any) -> None:
        nonlocal count
        if isinstance(value, dict):
            for v in value.values():
                walk(v)
        elif isinstance(value, list):
            if value:
                count += 1
            for v in value:
                walk(v)
        elif value not in (None, "", "unknown"):
            count += 1

    for key, value in rec.items():
        if key in ("id", "aliases", "conflicts"):
            continue
        walk(value)
    return count


def _winner(rec_a: dict[str, Any], rec_b: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    if _curated_rank(rec_a) != _curated_rank(rec_b):
        if _curated_rank(rec_a) > _curated_rank(rec_b):
            return rec_a, rec_b
        return rec_b, rec_a
    if _populated_count(rec_a) >= _populated_count(rec_b):
        return rec_a, rec_b
    return rec_b, rec_a


def classify_pair(rec_a: dict[str, Any], rec_b: dict[str, Any]) -> tuple[str, str]:
    """Decide how much trust a candidate pair deserves.

    Identical website URLs or identical normalised names are strong evidence of
    the same resource. Overlapping words are not: "cloud-speech-to-text" and
    "cloud-text-to-speech" are different products from the same provider, so
    those pairs are reported for review and never merged automatically.
    """
    wa = _website(rec_a)
    wb = _website(rec_b)
    da = (rec_a.get("urls") or {}).get("documentation")
    db = (rec_b.get("urls") or {}).get("documentation")
    if da and db and da == db:
        return "high", "identical_documentation"
    na = ids.normalize_name_for_match(rec_a.get("name") or "")
    nb = ids.normalize_name_for_match(rec_b.get("name") or "")
    if na and na == nb:
        return "high", "identical_name_same_provider"
    if wa and wb and wa == wb:
        # A shared homepage proves nothing: catalogs routinely point every
        # product of one provider at the same landing page.
        return "review", "shared_website"
    return "review", "similar_name_same_provider"


def find_duplicates(
    store: Any,
    *,
    threshold: float = 0.82,
    same_provider_only: bool = True,
    include_cross_provider: bool = False,
) -> list[dict[str, Any]]:
    """Find candidate duplicate pairs."""
    records = store.all()
    results: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def _add(a_id: str, b_id: str, score: float, reason: str, same_provider: bool,
             confidence: str = "review") -> None:
        key = tuple(sorted((a_id, b_id)))
        if key in seen:
            return
        seen.add(key)
        results.append({
            "a": a_id,
            "b": b_id,
            "score": float(score),
            "reason": reason,
            "same_provider": bool(same_provider),
            "confidence": confidence,
        })

    # Group by category then provider domain.
    by_category: dict[str, list[Any]] = {}
    for rec in records:
        by_category.setdefault(rec.get("category") or "unknown", []).append(rec)

    for category, recs in by_category.items():
        # Same provider groups.
        by_provider: dict[str, list[Any]] = {}
        for rec in recs:
            by_provider.setdefault(_provider_domain(rec) or "unknown", []).append(rec)

        for provider, group in by_provider.items():
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    ra, rb = group[i], group[j]
                    score = pair_score(ra, rb)
                    if score >= threshold:
                        confidence, reason = classify_pair(ra, rb)
                        _add(ra["id"], rb["id"], score, reason, True, confidence)

        # Cross-provider fuzzy when not restricted to same provider.
        if not same_provider_only:
            for i in range(len(recs)):
                for j in range(i + 1, len(recs)):
                    ra, rb = recs[i], recs[j]
                    if _provider_domain(ra) == _provider_domain(rb):
                        continue
                    score = pair_score(ra, rb)
                    if score >= threshold:
                        _add(ra["id"], rb["id"], score,
                             "similar_name_cross_provider", False, "review")

    # Cross-provider identical names.
    if include_cross_provider:
        by_name: dict[str, list[Any]] = {}
        for rec in records:
            by_name.setdefault(ids.normalize_name_for_match(rec.get("name") or ""), []).append(rec)
        for norm, group in by_name.items():
            if not norm:
                continue
            if len(group) < 2:
                continue
            for i in range(len(group)):
                for j in range(i + 1, len(group)):
                    ra, rb = group[i], group[j]
                    if ra.get("category") != rb.get("category"):
                        continue
                    if _provider_domain(ra) == _provider_domain(rb):
                        continue
                    _add(ra["id"], rb["id"], 1.0,
                         "identical_name_different_provider", False, "review")

    results.sort(key=lambda r: (-r["score"], r["a"], r["b"]))
    return results


def apply_merges(store: Any, pairs: list[dict[str, Any]], *,
                 force: bool = False) -> dict[str, int]:
    """Merge the losers from ``pairs`` into the winners.

    Only pairs classified as high confidence are merged unless ``force`` is set.
    """
    merged_count = 0
    skipped = 0
    for pair in pairs:
        if pair.get("confidence", "high") != "high" and not force:
            skipped += 1
            continue
        a_id = pair.get("a")
        b_id = pair.get("b")
        if not a_id or not b_id or a_id == b_id:
            skipped += 1
            continue
        rec_a = store.get(a_id)
        rec_b = store.get(b_id)
        if rec_a is None or rec_b is None:
            skipped += 1
            continue

        prov_a = _provider_domain(rec_a)
        prov_b = _provider_domain(rec_b)
        if prov_a != prov_b:
            names_identical = (
                ids.normalize_name_for_match(rec_a.get("name") or "")
                == ids.normalize_name_for_match(rec_b.get("name") or "")
            )
            wa = _website(rec_a)
            wb = _website(rec_b)
            same_reg_domain = False
            if wa and wb:
                ha = urlsplit(wa).hostname
                hb = urlsplit(wb).hostname
                same_reg_domain = (
                    ids.registrable_domain(ha) is not None
                    and ids.registrable_domain(ha) == ids.registrable_domain(hb)
                )
            if not (names_identical and same_reg_domain):
                skipped += 1
                continue

        winner_rec, loser_rec = _winner(rec_a, rec_b)
        winner_id = winner_rec.get("id")
        loser_id = loser_rec.get("id")

        # Merge loser into winner.
        merged_rec, _status = models.merge_into(
            copy.deepcopy(winner_rec),
            copy.deepcopy(loser_rec),
        )
        # Add loser id to aliases.
        aliases = list(merged_rec.get("aliases") or [])
        if loser_id not in aliases:
            aliases.append(loser_id)
        merged_rec["aliases"] = sorted(set(aliases))
        merged_rec = models.normalize_record(merged_rec)
        merged_rec["id"] = winner_id

        store.records[winner_id] = merged_rec
        try:
            store.dirty.add(winner_id)
        except Exception:
            pass
        store.remove(loser_id)
        merged_count += 1

    return {"merged": merged_count, "skipped": skipped}
