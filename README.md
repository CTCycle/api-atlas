# API Atlas

[![Validate catalog](https://github.com/CTCycle/api-atlas/actions/workflows/validate.yml/badge.svg)](https://github.com/CTCycle/api-atlas/actions/workflows/validate.yml)
[![License: MIT](https://img.shields.io/badge/code-MIT-blue.svg)](LICENSE)
[![Catalog: CC BY 4.0](https://img.shields.io/badge/catalog-CC%20BY%204.0-lightgrey.svg)](ATTRIBUTION.md)

A curated directory of APIs, public databases, open-data portals and MCP servers
for developers, researchers and AI agents.

**2,161 resources across 45 categories** (1,765 APIs, 262 portals, 77 datasets,
57 MCP servers). 527 rows verified by a maintainer; the rest are pointers with
working links.

The catalog is Markdown. Every resource is one row in one category file. Browse it
on GitHub, search it with the repository search box, or fetch the machine-readable
copy at [`data/catalog.jsonl`](data/catalog.jsonl).

This is a directory, not a platform. No accounts, no hosted service, no crawler.
Rows are added and corrected by people, and every row says where it came from.

## Browse by category

| Category | What is inside |
| --- | --- |
| [Agriculture](catalog/agriculture.md) | Crops, soils, farm economics, yields and agri-food statistics |
| [AI & Machine Learning](catalog/ai-ml.md) | Model inference, embeddings, speech, vision, training data and ML platforms |
| [Animals](catalog/animals.md) | Species data, pet and wildlife records, animal images and shelters |
| [Art & Design](catalog/art-design.md) | Museums, image collections, design assets, colour and typography data |
| [Blockchain & Cryptocurrency](catalog/blockchain-crypto.md) | Chain data, market prices, wallets, explorers and smart contract tooling |
| [Business & Commerce](catalog/business-commerce.md) | Company data, CRMs, invoicing, product catalogs and marketplaces |
| [Cloud & Infrastructure](catalog/cloud-infrastructure.md) | Hosting, storage, container and deployment platforms |
| [Communication](catalog/communication.md) | Email, SMS, voice, chat and notification services |
| [Data & Analytics](catalog/data-analytics.md) | Analytics platforms, event pipelines, BI and metrics services |
| [Developer Tools](catalog/developer-tools.md) | Version control, CI, code quality, package registries and build tooling |
| [Documents & Productivity](catalog/documents-productivity.md) | Document conversion, file storage, notes, tasks and office automation |
| [Economics](catalog/economics.md) | Macroeconomic indicators, trade, labour and price statistics |
| [Education](catalog/education.md) | Schools, universities, courses, learning content and academic records |
| [Energy](catalog/energy.md) | Electricity grids, fuel prices, renewables and emissions data |
| [Entertainment & Media](catalog/entertainment-media.md) | Film, television, music, books, podcasts and media metadata |
| [Finance](catalog/finance.md) | Banking, markets, payments data, forex and financial statements |
| [Food & Nutrition](catalog/food-nutrition.md) | Food composition, recipes, restaurants and product nutrition data |
| [Games](catalog/games.md) | Game databases, player stats, assets and community APIs |
| [Geospatial](catalog/geospatial.md) | Maps, geocoding, satellite imagery, elevation and boundary data |
| [Government & Public Sector](catalog/government.md) | Legislation, procurement, civic records and public sector APIs |
| [Health & Medical](catalog/health-medical.md) | Clinical trials, medical literature, health statistics and terminology |
| [Housing & Real Estate](catalog/housing-real-estate.md) | Property listings, prices, rents, permits and housing statistics |
| [Humanitarian & Development](catalog/humanitarian-development.md) | Aid flows, displacement, conflict events and development indicators |
| [Identity & Security](catalog/identity-security.md) | Authentication, breach data, vulnerability feeds and threat intelligence |
| [IoT & Devices](catalog/iot.md) | Device clouds, sensor networks and hardware telemetry |
| [Jobs & HR](catalog/jobs-hr.md) | Job boards, salary data, recruiting and workforce datasets |
| [Legal](catalog/legal.md) | Case law, statutes, court records and legal reference data |
| [Life Sciences](catalog/life-sciences.md) | Genomics, proteins, chemistry, pharmacology and biomedical datasets |
| [Manufacturing & Industry](catalog/manufacturing.md) | Industrial standards, materials, supply chains and factory data |
| [Marketing & Social](catalog/marketing-social.md) | Social platforms, advertising, audience and influencer data |
| [Mathematics](catalog/mathematics.md) | Mathematical sequences, proofs, symbolic computation and statistics |
| [MCP Servers](catalog/mcp-servers.md) | Model Context Protocol servers that expose tools and data to AI agents |
| [News & Journalism](catalog/news-journalism.md) | News archives, headlines, fact checking and media monitoring |
| [Open Data Portals](catalog/open-data.md) | National and international open data catalogs and CKAN portals |
| [Patents & IP](catalog/patent-ip.md) | Patent offices, trademarks and intellectual property records |
| [Payments](catalog/payments.md) | Payment processing, banking rails, tax and billing services |
| [Science & Research](catalog/science-research.md) | Publications, citations, physics, chemistry and earth observation |
| [Search](catalog/search.md) | Web, academic and specialist search engines |
| [Space & Astronomy](catalog/space.md) | Satellite tracking, astronomy archives, launches and orbital data |
| [Sports & Fitness](catalog/sports-fitness.md) | Scores, statistics, fitness tracking and sports data |
| [Telecommunications](catalog/telecommunications.md) | Phone numbers, carriers, number portability and messaging data |
| [Test Data](catalog/test-data.md) | Fake users, addresses, images and generators for testing |
| [Transportation & Logistics](catalog/logistics-transportation.md) | Transit, shipping, flights, routing and vehicle data |
| [Travel](catalog/travel.md) | Flights, hotels, places, transit and trip planning |
| [Weather & Climate](catalog/weather-climate.md) | Forecasts, observations, reanalysis and climate projections |

## How to read a row

```markdown
| [Open-Meteo](https://open-meteo.com/) | API | Weather forecasts, historical reanalysis and climate projections for any coordinate | Freemium | None | [CC BY 4.0](https://open-meteo.com/en/license) | [docs](https://open-meteo.com/en/docs) | editorial | 2026-10-24 |
```

- **Type**: `API`, `Dataset`, `Portal` (a catalog of datasets) or `MCP` (a Model Context Protocol server).
- **Access**: `Free`, `Free tier`, `Freemium`, `Paid` or `Restricted` (approval, institution or licence needed).
- **Auth**: `None`, `API key`, `OAuth`, `Registration` (free account) or `Account` (paid or approved account).
- **License**: what the provider states, linked where a licence page exists.
- **Source**: `editorial`, `public-apis`, `APIs.guru` or `awesome-datasets`. It records the origin of the row, not its quality.
- **Checked**: the date a person last read the official documentation and confirmed the row. `-` means nobody has confirmed it yet.

`-` means not established. It never means "probably fine". Full column rules are in
[docs/format.md](docs/format.md).

## Machine-readable copy

```bash
curl -O https://raw.githubusercontent.com/CTCycle/api-atlas/main/data/catalog.jsonl
```

Each line is one resource: `id`, `name`, `type`, `category`, `description`,
`website`, `docs`, `access`, `auth`, `license`, `source`, `checked`. A CSV copy is at
`data/catalog.csv`. Both are generated from the Markdown; if they disagree, the
Markdown is correct.

```python
import json
rows = [json.loads(l) for l in open("data/catalog.jsonl", encoding="utf-8")]
free = [r for r in rows if r["access"] == "Free" and r["auth"] == "None"]
print(len(free), "free, keyless APIs")
```

## Scope

What is in scope, and what is deliberately excluded, is defined in
[docs/inclusion-criteria.md](docs/inclusion-criteria.md). In short: real APIs,
datasets, portals and MCP servers with documentation and a working canonical link.
Not libraries, not SDKs, not individual services of a cloud platform, not
marketplace landing pages, not dead projects.

## Contributing

Add a row in the right category, in alphabetical order, and open a pull request. No
build step, no dependencies, no account.

```bash
python scripts/catalog.py validate
python scripts/catalog.py export --format jsonl
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for the row format and the review criteria,
or open the [add a resource](.github/ISSUE_TEMPLATE/add-resource.yml) issue form if
you would rather not edit files.

## Maintenance

`scripts/catalog.py` validates the tables, checks every link, exports the JSONL and
CSV copies, lists duplicates and builds a monthly report. It never edits the
catalog: reports are proposals that a person applies. See
[docs/maintenance.md](docs/maintenance.md).

## Limitations

- Coverage is uneven. Some categories have a dozen rows, some have more than a
  hundred, and the depth reflects what was checked rather than what exists.
- Most rows have no `Checked` date. They are unverified pointers with working links
  at the time of the last sweep, nothing more.
- Pricing and licence values are only as good as the provider's page on the day it
  was read. They change without notice.
- The catalog is not exhaustive and does not try to be. A missing resource is a
  contribution opportunity, not an error.

## Licence

- Code and tooling: MIT, see [LICENSE](LICENSE).
- Original compilation and editorial content: CC BY 4.0.
- Rows carried over from upstream catalogs keep their upstream licence. See
  [ATTRIBUTION.md](ATTRIBUTION.md).
