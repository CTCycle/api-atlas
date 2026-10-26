# Design notes

Why the catalog looks the way it does. Short version: it is a Markdown directory
with one small optional script, and that is deliberate.

## What this replaced

Version 1.0.0 was a registry: 5,227 records in 70 JSONL shards, a Python package
(`regipy`, about 3,800 lines), a JSON Schema with seven sub-objects per record, a
SQLite FTS index, three upstream importers and two scheduled workflows that
re-imported upstream catalogs and rewrote the shards monthly.

It answered questions like "free geospatial data with commercial use allowed" with
one command, but the data could not carry that weight. An audit of the 1.0.0 data
found:

| Problem | Count |
| --- | --- |
| Records with no description | 664 |
| Descriptions truncated mid-sentence upstream | 590 |
| Pricing model unknown | 5,138 of 5,227 |
| Access model unknown | 3,108 of 5,227 |
| Bulk cloud-service enumerations (Google, AWS, Azure, API Setu) | about 980 |
| Link checks that were only HTTP status pings | all |

The schema promised a level of metadata the sources never supplied. A developer
browsing the repository saw JSONL lines; a maintainer could not fix a row without
running an importer.

## What was kept

- Every row with a usable description and a live link, deduplicated by name and by
  canonical URL: 1,716 rows carried over, plus editorial additions.
- Provenance per row in the Source column, and upstream licences in ATTRIBUTION.md.
- The link-check semantics that worked: HEAD then GET, gated versus broken
  classification, retry before removal, no auto-deletion.
- The curated seed entries, which are the only rows with real verification dates.
- The complete 1.0.0 registry at tag `v1.0.0` and in git history.

## What was removed

- The package, the JSON Schema, the taxonomy YAML, the provider policy layer, the
  SQLite index, the importers, the unit tests and the monthly refresh workflow.
- The idea that a catalog needs a build step. Adding a row is now a text edit.
- Automatic rewriting of the catalog by anything other than a person.

## Lessons taken from public-apis

Adopted:

1. Markdown tables as the single source of truth, readable in the GitHub UI and in
   a diff.
2. Fixed, small vocabularies for the classification columns, validated in CI.
3. Name cell as the link to the official page, so rows stay narrow.
4. A hand-maintained index, with every category reachable in one click.
5. A format validator that fails the build, plus a link checker that runs outside
   the pull-request path.
6. A contribution checklist short enough that people actually follow it.

Rejected on purpose:

1. One 2,700-line README. Categories are separate files, so a pull request touches
   one file and reviewers see a small diff.
2. Rules that are documented but not enforced. Alphabetical order, allowed values
   and column count are checked, not requested.
3. Promotional tables and banners inside the data. The catalog has no ad slots.
4. A minimum of three entries per category, which invites padding. A thin category
   is honest; filler is not.
5. Silent rot. Every row carries a source and, where a person confirmed it, a date.

## Known limitations

- Most rows have no verification date. They are pointers with working links, not
  audited claims.
- Access and licence values are inherited from upstream listings for the carried
  over rows. Only the `editorial` rows were read from provider documentation.
- Category assignment is editorial and sometimes debatable. A resource in the
  "wrong" category is a one-line fix.
- The catalog does not attempt completeness. Coverage reflects what was checked.
