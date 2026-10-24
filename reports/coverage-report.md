# Catalog coverage report

Generated 2026-10-24 by `python scripts/report.py` from the JSONL shards.

## Size

- Records: 5227
- APIs: 4117, datasets: 1110
- Distinct provider identities: 3013
- Records merged from more than one source: 172
- Curated records (manual review): 90
- Categories populated: 45 of 49 (92%)

### Records per upstream source

| Source | Records |
|---|---:|
| apis-guru | 2530 |
| public-apis | 2059 |
| awesome-public-datasets | 1098 |
| curated | 90 |

A record can appear under several sources, so these numbers sum to more than the total.

## Verification

| Tier | Records | Share |
|---|---:|---:|
| verified | 88 | 1.7% |
| partial | 4241 | 81.1% |
| imported | 898 | 17.2% |

Status: active 4327, unverified 550, unavailable 350

## Access and pricing

| Field | Value | Records | Share |
|---|---|---:|---:|
| access.model | unknown | 3108 | 59.5% |
| access.model | public | 1046 | 20.0% |
| access.model | api_key | 917 | 17.5% |
| access.model | oauth | 139 | 2.7% |
| access.model | restricted | 9 | 0.2% |
| access.model | registration | 8 | 0.2% |
| pricing.model | unknown | 5138 | 98.3% |
| pricing.model | free | 47 | 0.9% |
| pricing.model | freemium | 26 | 0.5% |
| pricing.model | paid | 16 | 0.3% |
| license.commercial_use | unknown | 5156 | 98.6% |
| license.commercial_use | allowed | 58 | 1.1% |
| license.commercial_use | restricted | 13 | 0.2% |

Records with a named licence: 989 (18.9%). Records with a known pricing model: 89 (1.7%).

## Category coverage

| Category | Records | APIs | Datasets | Named licence | Verified |
|---|---:|---:|---:|---:|---:|
| agriculture | 18 | 0 | 18 | 3 | 0 |
| ai-ml | 248 | 132 | 116 | 17 | 9 |
| animals | 24 | 24 | 0 | 0 | 0 |
| art-design | 78 | 68 | 10 | 1 | 0 |
| blockchain-crypto | 113 | 113 | 0 | 0 | 0 |
| business-commerce | 198 | 198 | 0 | 38 | 3 |
| climate-environment | 28 | 28 | 0 | 1 | 1 |
| cloud-infrastructure | 568 | 566 | 2 | 275 | 0 |
| communication | 89 | 89 | 0 | 12 | 0 |
| data-analytics | 315 | 277 | 38 | 274 | 0 |
| developer-tools | 415 | 398 | 17 | 71 | 0 |
| documents-productivity | 101 | 101 | 0 | 4 | 0 |
| earth-sciences | 17 | 0 | 17 | 3 | 0 |
| economics | 126 | 3 | 123 | 10 | 5 |
| education | 17 | 3 | 14 | 0 | 0 |
| energy | 35 | 5 | 30 | 2 | 8 |
| entertainment-media | 316 | 303 | 13 | 17 | 0 |
| finance | 174 | 123 | 51 | 24 | 4 |
| food-nutrition | 36 | 36 | 0 | 3 | 0 |
| games | 114 | 111 | 3 | 2 | 0 |
| geospatial | 162 | 157 | 5 | 15 | 11 |
| government | 327 | 126 | 201 | 18 | 4 |
| health-medical | 111 | 50 | 61 | 13 | 6 |
| identity-security | 114 | 103 | 11 | 9 | 0 |
| interdisciplinary | 3 | 0 | 3 | 0 | 0 |
| iot | 17 | 17 | 0 | 4 | 0 |
| jobs-hr | 36 | 36 | 0 | 0 | 0 |
| life-sciences | 52 | 4 | 48 | 7 | 5 |
| logistics-transportation | 223 | 180 | 43 | 7 | 4 |
| marketing-social | 122 | 87 | 35 | 12 | 0 |
| neuroscience | 16 | 0 | 16 | 0 | 0 |
| news-journalism | 26 | 26 | 0 | 0 | 0 |
| open-data | 382 | 355 | 27 | 37 | 3 |
| patent-ip | 4 | 4 | 0 | 0 | 0 |
| payments | 51 | 51 | 0 | 4 | 6 |
| physical-sciences | 11 | 0 | 11 | 1 | 0 |
| science-research | 64 | 62 | 2 | 12 | 8 |
| search | 19 | 6 | 13 | 2 | 0 |
| social-sciences | 63 | 0 | 63 | 6 | 1 |
| sports-fitness | 91 | 65 | 26 | 2 | 0 |
| telecommunications | 86 | 58 | 28 | 48 | 0 |
| test-data | 36 | 36 | 0 | 0 | 0 |
| travel | 4 | 4 | 0 | 0 | 0 |
| unknown | 96 | 63 | 33 | 18 | 0 |
| weather-climate | 81 | 49 | 32 | 17 | 10 |

Empty categories: legal, manufacturing-industry, mathematics, space.

## Gaps

- Records without a description: 664 (12.7%).
- Records with unknown pricing: 5138 (98.3%).
- Records with unknown commercial use: 5156 (98.6%).
- Records flagged for review: 0.

Pricing and licensing are the least complete fields because two of the three upstream
catalogs do not record them at all. Licensed coverage improves through curated seeds and
provider policies, not through inference.

## Limitations

- Imported records carry the upstream description. They are not independently confirmed.
- An HTTP 200 proves a URL answers, not that the API works, the quota holds or the
  licence statement is current.
- Free tier limits are only present where a curated entry quotes the provider page;
  absence means unknown, not unlimited.
- Coverage is uneven across categories because it mirrors the upstream catalogs.
- Categories with fewer than ten records should be treated as thin.

## Refresh procedure

1. `python -m regipy.cli import all` re-imports all three upstream catalogs and the seeds.
2. `python -m regipy.cli enrich` re-applies provider policies and category inference.
3. `python -m regipy.cli linkcheck --max-age-days 30` re-verifies URLs and dates.
4. `python -m regipy.cli dedupe` reviews candidates; `merge` applies a reviewed pair.
5. `python -m regipy.cli build` rebuilds the index, `validate` gates the result.
6. `python scripts/report.py` regenerates this file.

## Future improvements

- Enrich the imported long tail with per provider quotas, formats and coverage.
- Add more institutional and paid sources, where the catalog is thinnest.
- Snapshot upstream catalog versions in provenance so a refresh is diffable.
- Grow the verification sample beyond URL reachability into documented capability checks.
