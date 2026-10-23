# Contributing

## Adding a single entry

Via the command line:

```bash
python -m regipy.cli import curated
```

Or edit the relevant shard directly. Add one JSON object per line to `catalog/apis/<category>.jsonl` or `catalog/datasets/<category>.jsonl`. Keep keys sorted and use deterministic serialisation. Run `python -m regipy.cli validate` before submitting.

## Curated seed entries

Editorial knowledge lives in `curation/seeds/*.yaml`. Files are merged into the shards by `python -m regipy.cli import curated`, and curated values always win over imported ones. Add to an existing themed file rather than creating a new one.

```yaml
version: 1
source: curated
entries:
  - name: Open-Meteo
    kind: api
    category: weather-climate
    description: Weather forecasts and historical reanalysis for any coordinate.
    type: rest
    provider: open-meteo.com
    website: https://open-meteo.com/
    documentation: https://open-meteo.com/en/docs
    access: public
    pricing: freemium
    free_tier_limits: Non-commercial use is free, commercial plans are paid.
    pricing_basis: official_docs
    license: CC BY 4.0
    license_spdx: CC-BY-4.0
    license_url: https://open-meteo.com/en/license
    commercial_use: restricted
    attribution_required: true
    license_basis: official_docs
    geographic: Global
    temporal: 1940 to present
    formats: [json]
    update_frequency: hourly
    tags: [forecast, historical]
    confidence: verified
    verified_on: "2026-10-23"
```

`confidence: verified` requires `verified_on`, which must be the date the cited pages were actually read. Use `confidence: partial` and omit `verified_on` when you filled fields from documentation but did not confirm the whole record. Omitted fields stay unknown.

## Field by field rules

- Never invent values. If a value is not known, use `null` or `unknown`.
- Cite official documentation in `license.basis`, `pricing.basis` and `verification.notes` where possible.
- Set `verification.confidence` honestly: `imported` when unchecked, `partial` when HTTP checked or supported by editorial metadata, `verified` only when key metadata is confirmed against official documentation.
- Do not claim `license.commercial_use` as `allowed`, `restricted` or `prohibited` without a `license.name` as evidence. The validator rejects such claims.
- Use categories from `schema/taxonomy.yaml`. Unknown categories become `unknown`.
- Use allowed enum values for `kind`, `type`, `access.model`, `pricing.model`, `license.commercial_use`, `update_frequency` and `status`.
- Keep descriptions concise and factual.

## Running the checks

```bash
python -m regipy.cli import all
python -m regipy.cli build
python -m regipy.cli validate
python -m regipy.cli linkcheck --limit 300 --max-age-days 7
```

## Pull request checklist

- [ ] Records validate with `python -m regipy.cli validate`.
- [ ] Unit tests pass with `python -m unittest discover -s tests -v`.
- [ ] No invented values; unknowns are `null` or `unknown`.
- [ ] Provenance is present for every record.
- [ ] `license.commercial_use` claims include a licence name.
- [ ] Shard files remain one JSON object per line with sorted keys.
- [ ] Documentation updated if behaviour changed.

## Flagging outdated records

Use the `flag` subcommand to mark a record for review:

```bash
python -m regipy.cli flag <entry-id>
```

Review open flags with:

```bash
python -m regipy.cli flags
```

A flag records the date and reason. Maintainers triage flags during the scheduled deduplication and re-import reviews.