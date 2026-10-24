# Deduplication review

Generated 2026-10-24 during the v1.0.0 finalisation pass.

## Summary

- Candidate pairs reviewed: 20
- High confidence (auto-mergeable): 0
- Merges applied: 0
- Reason for every candidate: `shared_website` (two distinct products from the same provider that point at the same landing page)

## Method

`python -m regipy.cli dedupe` was run with the default threshold (0.82) and same-provider grouping. All 20 candidates share a provider domain and a website URL, but their normalised names differ, so `classify_pair` correctly rates them `review` rather than `high`. None of them are the same real-world service:

- AWS/Azure/Google service families where each entry is a separate API (for example `amazon-route-53` vs `amazon-route-53-domains` vs `amazon-route-53-resolver`).
- Interzoid endpoints that are distinct operations behind one provider site.
- Government data portals that aggregate several datasets.

No merge was applied. The records keep their separate identities and provenance.

## Policy going forward

- `dedupe` is run as part of the monthly refresh cycle (see `.github/workflows/refresh.yml`).
- Only `high` confidence pairs (identical documentation URL or identical normalised name within one provider) are merged automatically.
- `review` pairs are listed in `reports/dedupe-candidates.json` each run for a human pass; merges can be applied explicitly with `python -m regipy.cli merge <winner> <loser>`.
- Cross-provider identical names are not in scope for v1 and are only checked with `--cross-provider`.

## Tail enrichment status

`enrich` reported 0 changed records on the final pass because provider policies and category inference were already applied during import. Remaining enrichment work is tracked as future improvements in `reports/coverage-report.md`:

- 663 records without a description (12.7%)
- Pricing still unknown for 98.3% of records (upstream catalogs do not record it)
- Commercial use still unknown for 98.7% of records
- Access model still unknown for 59.5% of records
