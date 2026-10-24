# Maintenance

## Scheduled jobs

The refresh cycle is automated in `.github/workflows/refresh.yml` (monthly, first day of the month, plus `workflow_dispatch`). The weekly link check is in `.github/workflows/validate.yml`.

- Weekly: link check a bounded sample of records (GitHub Actions, Mondays 06:00 UTC).
- Monthly: full link check sweep across the catalog.
- Monthly: deduplication review of merged and flagged records.
- Monthly: re-import of all three upstream catalogs.
- Quarterly or on upstream release: manual review of the refresh diff before merging.

Example commands:

```bash
python -m regipy.cli linkcheck --limit 300 --max-age-days 7
python -m regipy.cli dedupe
python -m regipy.cli import all
python -m regipy.cli build
python -m regipy.cli validate
```

Last manual full refresh: 2026-10-24 (v1.0.0), 5227 records, 0 validation errors, 42 tests passing.

## What each check can prove

- `validate`: structural correctness against the JSON Schema and semantic rules. It proves field types, enums, category membership and licence evidence. It cannot prove that a URL resolves or that a licence statement is true.
- `linkcheck`: that a URL responds and with which status code. It records the result in verification fields. It cannot prove that content matches the description or that access still works after authentication.
- `dedupe`: that records share a provider and name key. It cannot prove that two records describe the same real world service.
- `import`: that upstream entries were transformed into the schema. It cannot verify upstream accuracy.

## What each check cannot prove

- No automated check confirms pricing, rate limits or licence terms against the provider website.
- No check confirms that a dataset still matches its described coverage or format.
- Link checks cannot bypass authentication or bot protection.

## Interpreting a broken link

A non 2xx or 3xx response is recorded as a broken link. Before marking a record unavailable:

1. Retry manually, because transient failures and rate limits are common.
2. Check whether the provider moved the page.
3. If the endpoint is permanently gone, set `status` to `unavailable` and add a flag.
4. If only the documentation moved, update `urls.documentation` and keep `status` as `active`.

## Interpreting a gated endpoint

A gated endpoint may return 401, 403 or 429. This is not necessarily a broken link:

- 401 or 403 often means an API key or login is required. Check `access.model` and `urls.signup`.
- 429 means rate limiting. Retry later or reduce request volume.
- Some providers block automated requests entirely. Record `http_status` and note the gating in `verification.notes` rather than marking the record unavailable.

## Re-importing upstream catalogs

Re-import with `python -m regipy.cli import all`. Merging keeps curated values and records conflicts. After re-import, run `build`, `validate` and review `dedupe` output. Check the diff of changed shards before committing.