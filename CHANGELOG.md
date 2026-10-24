# Changelog

## 2.0.0 (unreleased)

The registry became a catalog. The machine-readable registry of 5,227 records was
replaced by a curated Markdown directory, and the Python package, the JSON Schema,
the SQLite index, the importers and the scheduled refresh workflows were removed.

### Changed

- Catalog source of truth is now one Markdown table per category in `catalog/`,
  edited by hand. No build step is needed to contribute.
- Row format: Name, Type, Description, Access, Auth, License, Docs, Source, Checked.
- 42 categories, including new `legal`, `mathematics`, `space`, `manufacturing` and
  a separate `mcp-servers` page for Model Context Protocol servers.
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
