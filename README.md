# API Atlas

A curated, machine readable registry of APIs, public databases and downloadable datasets. Each entry is a single JSON object with normalised fields for access, pricing, licensing, coverage and verification status. The catalog is stored as JSONL shards and can be queried through a small command line interface.

## What this is

This project collects public APIs and datasets into one consistent schema. It records what a source offers, how to reach it, what it costs, what its licence allows, how often it updates and how much of that metadata has actually been checked. Every record carries provenance back to the upstream catalog it came from.

## Why it exists

Public API and dataset lists are scattered, inconsistently described and rarely carry licence or access information. This registry normalises those details into a queryable catalog so that a question such as "free geospatial data with commercial use allowed" can be answered with one command. Verification tiers make clear which values are imported and which have been checked.

## Quickstart

```bash
python -m pip install -e .
python -m regipy.cli stats
```

Import upstream catalogs, build the SQLite index, then query it:

```bash
python -m regipy.cli import all
python -m regipy.cli build
python -m regipy.cli search "weather" --limit 10
```

## Repository layout

```text
api-atlas/
  catalog/          JSONL shards, source of truth
    apis/
    datasets/
  data/            derived SQLite index (built locally)
  docs/            schema, usage and maintenance docs
  regipy/          Python package
  reports/         generated reports
  schema/          JSON Schema, taxonomy and provider policies
  tests/           test suite
  .github/         CI workflow
```

## How the catalog is organised

Catalog files are JSONL shards at `catalog/apis/<category>.jsonl` and `catalog/datasets/<category>.jsonl`. Each line is one record. Keys are sorted and serialisation is deterministic. These files are the source of truth. The SQLite database at `data/registry.sqlite` is a derived index rebuilt with `python -m regipy.cli build`.

Categories come from `schema/taxonomy.yaml`. A record that cannot be classified uses the `unknown` category and is triaged later.

## Verification tiers

- imported: never checked. `verification.method` is `upstream_import` and `verification.confidence` is `imported`.
- partial: HTTP checked or supported by editorial metadata. `verification.confidence` is `partial`.
- verified: checked and key metadata confirmed against official documentation. `verification.confidence` is `verified`.

Status values are `active`, `deprecated`, `unavailable` and `unverified`.

Unknown values are stored as `null` or the string `unknown`. The validator rejects a `license.commercial_use` claim when no licence name is present as evidence.

## Data sources and licensing

Upstream baselines actually used:

- public-apis/public-apis, MIT licence.
- APIs.guru openapi-directory, CC0-1.0.
- awesomedata/awesome-public-datasets, MIT licence.

Project code is released under the MIT licence. Catalog data is offered under CC BY 4.0. Records derived from an upstream source keep that upstream licence, and the per record provenance carries the licence string. See ATTRIBUTION.md for the full obligations.

## Query examples

```bash
python -m regipy.cli stats
python -m regipy.cli categories
python -m regipy.cli search "geocoding" --category geospatial --limit 20
python -m regipy.cli show <entry-id>
python -m regipy.cli alternatives <entry-id> --pricing free
python -m regipy.cli export --format csv --out reports/export.csv
```

## Maintenance summary

Link checks run on a bounded sample each week and on the full catalog each month. Deduplication and re-import of upstream catalogs are scheduled reviews. See docs/maintenance.md.

## Limitations

- Coverage depends on upstream catalogs and is uneven across categories.
- Imported records are not verified. Treat `imported` confidence as unconfirmed.
- Licence information is only as complete as the upstream source or a provider policy. Many records remain `unknown`.
- The SQLite index is derived and must be rebuilt after catalog changes.
- Entry counts are not hardcoded. Run `python -m regipy.cli stats` for the current total.

## Contributing

See CONTRIBUTING.md.