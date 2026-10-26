# Changelog

## 2.0.0 (unreleased)

The registry became a catalog. The machine-readable registry of 5,227 records was
replaced by a curated Markdown directory, and the Python package, the JSON Schema,
the SQLite index, the importers and the scheduled refresh workflows were removed.

### Polish pass (2026-10-26)

- Added `tests/test_catalog.py` (8 tests) covering parsing, allowed values,
  ordering and duplicate detection.
- Added `.github/workflows/linkcheck.yml` for a monthly scheduled full link check.
- Added `docs/comparison.md` comparing API Atlas with public-apis, brandonhimpfen/awesome-apis
  and Kikobeats/awesome-api.
- Added `.github/ISSUE_TEMPLATE/config.yml` to disable blank issues.
- Removed obsolete v1 reports (`answer-checks.md`, `coverage-report.md`,
  `dedupe-review.md`).
- Trimmed three truncated descriptions; added one verified row (Random User Generator).
- README badges, quick stats and a JSONL usage example.
- Disabled GitHub Projects; kept Issues enabled.

### Changed

- Catalog source of truth is now one Markdown table per category in `catalog/`,
  edited by hand. No build step is needed to contribute.
- Row format: Name, Type, Description, Access, Auth, License, Docs, Source, Checked.
- 1,921 rows across 42 categories, including new `legal`, `mathematics`, `space`,
  `manufacturing` pages and a separate `mcp-servers` page (57 servers).
- 229 URLs updated to their canonical targets after a full link check of 1,969 URLs;
  69 cross-domain redirects are queued for manual review.
- `scripts/catalog.py` (stdlib only) replaces the `regipy` package. It validates,
  exports JSONL and CSV, checks links and writes maintenance reports. It never
  edits the catalog.
- `data/catalog.jsonl` and `data/catalog.csv` are generated copies for scripts and
  agents, checked in CI for freshness.
- One validation workflow plus a manual link-check workflow. The monthly automatic
  refresh was removed: upstream re-imports and link-check fixes are human decisions.

### Removed

- `regipy/` package, `schema/entry.schema.json`, `schema/taxonomy.yaml`,
  `schema/provider-policies.yaml`, `data/registry.sqlite`, `tests/`, `curation/`,
  `scripts/report.py`, `scripts/answer_checks.py`, `.upstream/`, `ARCHITECTURE.md`.
- Import automation for public-apis, APIs.guru and awesome-public-datasets.

### Preserved

- Entries with a usable description and a live link, deduplicated and re-categorised.
- Provenance per row in the Source column, and upstream licences in ATTRIBUTION.md.
- The complete 1.0.0 registry remains available at tag `v1.0.0` and in git history.

## 1.0.0 (2026-10-24)

- First release: 5,227 records across 45 categories, SQLite index, CLI, link check
  and refresh workflows.

### Stage 2 (in progress)

- Cross-domain redirect triage: 8 dead rows removed; 61 redirects applied; 14 broken/DNS rows fixed.
- 8 of 10 partial dataset portals verified in-browser with docs URLs and Checked dates.
- All 300 thinnest inherited descriptions rewritten with researched, factual text.
- Full link check (2,125 URLs): 1,762 ok, 241 redirect, 47 gated, 25 TLS, 27 timeout, 14 error, 7 unreachable, 2 broken (fixed).
- Repository description and 10 topics set.
