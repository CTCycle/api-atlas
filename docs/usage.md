# Usage recipes

Commands below use `python -m regipy.cli`. After `pip install -e .` you may use the `regipy` shorthand. Run `python -m regipy.cli build` first if you have changed the catalog.

## Historical weather for Europe

Find weather datasets with historical coverage and European scope:

```bash
python -m regipy.cli search "historical weather" --category weather-climate --kind dataset --access public
python -m regipy.cli search --category weather-climate --update-frequency daily --limit 30
```

Inspect a candidate:

```bash
python -m regipy.cli show <entry-id>
```

## Free geospatial data with commercial use allowed

```bash
python -m regipy.cli search --category geospatial --kind dataset --pricing free --commercial allowed
python -m regipy.cli search --category geospatial --commercial allowed --limit 50
```

Export the results:

```bash
python -m regipy.cli export --format csv --out reports/geospatial-commercial.csv --category geospatial --pricing free --commercial allowed
```

## Downloadable medical datasets without authentication

```bash
python -m regipy.cli search --category health-medical --kind dataset --access public
python -m regipy.cli search --category health-medical --access public --format csv
```

## Freemium providers with rate limits

List freemium APIs and inspect their free tier limits:

```bash
python -m regipy.cli search --pricing freemium --limit 50
python -m regipy.cli show <entry-id>
```

Export for comparison:

```bash
python -m regipy.cli export --format jsonl --out reports/freemium.jsonl --pricing freemium
```

## Alternatives to a paid API

Find alternatives and restrict to free or freemium options:

```bash
python -m regipy.cli alternatives <entry-id>
python -m regipy.cli alternatives <entry-id> --pricing free
python -m regipy.cli alternatives <entry-id> --pricing freemium --access public
```

## Realtime versus historical sources

Realtime sources:

```bash
python -m regipy.cli search --update-frequency realtime --limit 50
```

Slowly changing or static sources:

```bash
python -m regipy.cli search --update-frequency static --limit 50
python -m regipy.cli search --update-frequency periodic --limit 50
```

Filter by provider or verification date:

```bash
python -m regipy.cli search --provider noaa.gov
python -m regipy.cli search --verified-since 2026-01-01 --confidence verified
```

## General filtering

Shared filter flags for `search`, `export` and `alternatives`:

`--category`, `--kind`, `--pricing`, `--access`, `--commercial`, `--status`, `--confidence`, `--format`, `--update-frequency`, `--verified-since`, `--provider`, `--limit`.

Show a single record and its provenance:

```bash
python -m regipy.cli show <entry-id>
```

List categories:

```bash
python -m regipy.cli categories
```

Current totals:

```bash
python -m regipy.cli stats
```
