# Architecture

## Overview

The registry is a small Python package (`regipy`) plus a catalog of JSONL files. The catalog files are the source of truth. The package provides schema validation, normalisation, merging, identifier helpers and a command line interface. A SQLite database is a derived index used for fast search.

## Components

- `regipy/schema.py` loads `schema/entry.schema.json`, `schema/taxonomy.yaml` and `schema/provider-policies.yaml`. It validates records and maps upstream categories to the internal taxonomy.
- `regipy/models.py` builds blank records, infers formats, normalises records and merges records with curation aware rules.
- `regipy/ids.py` normalises URLs, derives provider identity, slugifies names and creates duplicate detection keys.
- `regipy/store.py` loads and saves JSONL shards under `catalog/`, groups records by kind and category, merges duplicates and writes deterministic output.
- `regipy/cli.py` (command line interface) exposes the subcommands listed in the README. It is installed as the `regipy` console script by `pyproject.toml`.

## Data flow

1. Importers read an upstream catalog and call `models.new_record` for each entry.
2. `Store.upsert` normalises the record, applies provider policies when the licence is empty, detects duplicates by provider domain plus name and merges into any existing record.
3. `Store.save` rewrites only changed shards, one JSON object per line with sorted keys.
4. `regipy build` creates or rebuilds `data/registry.sqlite` from the shards.
5. Query commands read the SQLite index for speed and fall back to the shards when needed.

## Storage model

- `catalog/apis/<category>.jsonl` and `catalog/datasets/<category>.jsonl`: one record per line, source of truth.
- `data/registry.sqlite`: derived index, safe to delete and rebuild.
- `reports/`: generated validation, link check and deduplication reports.
- `.upstream/`: cached upstream snapshots, ignored by git.

## Record model

A record has a stable id of the form `provider-domain/slug`, a kind (`api` or `dataset`), a category, provider block, URL block, access, technical, pricing, licence, coverage, formats, update frequency, status, verification, curation, provenance and optional aliases, conflicts, flags and notes. Unknown values are `null` or `unknown`.

## Merging rules

Imports never reset verification or status fields. Curated records are not overwritten by imported ones. Among imported records, non empty values win and longer descriptions replace shorter ones. Provenance is appended per upstream source. Conflicts are recorded when a curated value replaces an existing one.

## Duplicate detection

Duplicates are detected with a key built from the provider domain and a normalised name. Provider identity keeps the first path segment for hosted project domains such as `github.io` so unrelated projects do not collapse into one provider.

## Validation

`regipy validate` runs JSON Schema validation plus semantic checks: category membership, kind and type compatibility, URL shape, licence evidence for commercial use claims, pricing consistency and provenance presence. Validation is also run in CI.

## Licensing model

Code is MIT. Catalog data is CC BY 4.0. Records derived from upstream sources retain their upstream licence and attribution. Provider level policies in `schema/provider-policies.yaml` fill missing licence fields only when the provider publishes citable terms. Per record provenance carries the licence string.