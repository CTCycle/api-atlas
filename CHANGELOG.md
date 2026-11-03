# Changelog

## 2.0.0 (unreleased)

The registry became a catalog. The machine-readable registry of 5,227 records was
replaced by a curated Markdown directory, and the Python package, the JSON Schema,
the SQLite index, the importers and the scheduled refresh workflows were removed.

### Release readiness (2026-11-03)

- Full re-verification: 2,887 URLs, 2,640 reachable, 58 moved, 95 gated, 34
  timeouts, 26 server errors, 15 TLS errors, 7 unreachable, 4 broken, 4 with an
  incomplete certificate chain, 2 DNS failures, 2 redirect loops.
- 9 rows removed with evidence: `Changelogs.md` (domain now a hosting coupon site),
  `Tradeworks` (product gone, domain redirects to a MetaTrader listing), `FakeJSON`
  (redirect chain to an unrelated spam host), `ProxyKingdom` and `DocStruct` (hosts
  no longer resolve), `VoxOdds` (service archived and switched off), `UK Public
  Tenders by Trade` (API answers 410), `Allowly Hiring Evidence` (documentation path
  404) and `APIXU` (duplicate of the existing Weatherstack row).
- 8 rows renamed or repointed after a verified move: Messari to Blockworks API,
  Google Gemini to Gemini API, Twitter to X API, Cisco Spark to Webex API, Slack
  documentation to `docs.slack.dev`, Magento to Adobe Commerce, Octopus Energy to
  the Kraken developer portal, and Covid-19 Datenhub to its credential-gated host
  with `Restricted` and `Account`.
- 3 duplicate rows merged, each listed once now: CoinGecko, OurAirports and the
  Aether-X port congestion oracle.
- `tests/test_export.py` checks the committed JSON, JSONL and CSV against
  `data/catalog.schema.json` and requires unique ids; CI runs it.
- Release surface added: `SECURITY.md`, `CODE_OF_CONDUCT.md`, and a release
  checklist split into before, at and after the visibility flip.
- Catalog: 2,541 rows (2,112 APIs, 286 portals, 76 datasets, 67 MCP servers).

### Verification pass (2026-10-29)

Full re-verification of every row, 2,496 URLs, with redirects followed to the real
destination: 2,282 reachable, 51 moved, 78 gated, 33 timeouts, 22 TLS errors, 20
server errors, 3 DNS failures, 3 unreachable, 2 parked domains, 1 broken, 1 redirect
loop. Four pages carried retirement wording.

- `linkcheck` was replaced in practice by a new `verify` command: it follows the
  redirect chain, resolves relative `Location` headers (the previous report proposed
  fragments such as `/Help.aspx#JavaScript` as new URLs), records the final URL and
  page title, and flags parked or expired domains plus retirement notices.
- New `triage` command groups the newest verify report by the decision each row
  needs: remove-or-replace, retired, confirm-new-domain, auth-mismatch,
  title-mismatch, update-url, recheck. It never edits anything.
- 17 rows removed with evidence: eight domains that now redirect to an unrelated
  spam host (`faceapi`, `ocr`, `translate`, `rates`, `iplocation` on `hirak.site`,
  plus `AniAPI`, `Fun Fact` and `Drivet URL Shortener`), two parked domains
  (`blague.xyz`, `docs.bhagavadgitaapi.in`), two domains that no longer resolve
  (`waifu.im`, `api.noctuasky.com`), two closed services (`owo.vc`, `LocalBitcoins`),
  one API withdrawn by its provider (`Kiprio Email Validate`, HTTP 410), one retired
  platform (`Custom Image Search Client`: Bing Search APIs were retired 2025-08-11),
  and one row pointing at the provider's own not-found page (`Neotimo DGFiP Mirror`).
- 15 rows corrected after a verified move: `gate.io` to `gate.com`,
  `shikimori.one` to `shikimori.io`, Octopus Energy's developer portal to the Kraken
  domain, the NYT Archive API (was pointing at the nytimes.com homepage), Mastercard
  Personalized Offers (was pointing at mastercard.com), the CFPB developer site,
  NCBI Taxonomy, Coinbase, Neon docs, Longdo docs, the Mozilla HTTP Observatory API
  path, the Grafana MCP docs, `data.gov.uk`, the French address API docs and the
  Semantic Scholar API page.
- Deliberately left alone: gated pages that are bot walls rather than auth
  requirements (`federalregister.gov`), cosmetic locale or `www` redirects, and any
  row that failed once (a single automated failure never removes a row).
- `scripts/probe.py` added: it discovers OpenAPI and Swagger documents on the
  website, in the docs page and at conventional paths, and only records a hit when
  the document parses and has a non-empty `paths` object. It follows redirects to
  the document's final URL, treats a docs URL that is itself a specification file as
  a candidate (83 rows point straight at `/openapi.json` or `/swagger.json`), and
  parses YAML when PyYAML is installed.

### Agent-facing additions (2026-10-29)

- `data/catalog.schema.json`, JSON Schema 2020-12 for the machine-readable rows.
- `data/catalog.json` (array) alongside the existing JSONL and CSV.
- Three derived, date-stable fields in every export: `verified`, `docs_present`,
  `license_known`. They do not change because a day passed, so the CI freshness
  check keeps its meaning.
- `validate` now also checks that the committed export matches the tables field for
  field, instead of relying on a separate CI step.
- `docs/no-auth.md` is generated from the catalog: every free, keyless resource,
  grouped by category.
- CI validates all generated artifacts and the monthly job now runs
  `verify` + `triage` + `probe` instead of a bare link check.

### Expansion pass (2026-10-29)

- 416 rows added from public-apis, the resources that list has and this catalog did
  not: 56 in `finance`, 43 in `entertainment-media`, 35 in `developer-tools`, 33 in
  `games`, 28 in `government`, 26 in `art-design`, 26 in
  `logistics-transportation`, 14 each in `cloud-infrastructure`,
  `documents-productivity`, `marketing-social`, 13 in `science-research`, 12 each in
  `animals`, `blockchain-crypto` and `jobs-hr`, 10 in `mcp-servers`, and the rest
  spread over 12 categories.
- Every candidate URL was fetched before merging. 5 of the returned rows were then
  dropped as dead, parked or duplicate, on top of 294 of the 715 upstream candidates
  rejected earlier for DNS failure, 404/410, parked domains, aggregator roots,
  cloud-service pages or duplication against the existing catalog.
- The 280 rows whose upstream blurb was shorter than 40 characters were rewritten
  against the live page before merging, so the catalog still has no description
  under 40 characters. Four same-name collisions (`Cat Facts`, `Dog Facts`) were
  disambiguated by provider.
- Carried rows keep `Source: public-apis` and `Checked: -`: they were link-checked
  and described from the live page, not read by a person.
- Catalog: 2,553 rows (2,122 APIs, 287 portals, 77 datasets, 67 MCP servers).

### Expansion pass (2026-10-26)

- Added 246 verified rows across 22 categories: 18 in `data-analytics`; 14 each in
  `agriculture`, `cloud-infrastructure`, `humanitarian-development` and
  `life-sciences`; 12 each in `education`, `housing-real-estate`, `iot`,
  `patent-ip` and `travel`; 11 in `health-medical`; 10 each in `animals`,
  `energy`, `open-data`, `space` and `telecommunications`; 9 each in `legal`,
  `manufacturing` and `mathematics`; 8 each in `economics`, `government` and
  `search`.
- Three new categories: `agriculture`, `housing-real-estate`,
  `humanitarian-development`. 45 categories in total.
- Every new URL was checked with a GET request before merging; 17 researched
  rows were dropped as duplicates of existing entries.
- Full link sweep of 2,497 URLs after the merge: 2,144 answered 200, 220
  redirected, 58 gated, 75 failed (30 timeouts, 23 TLS handshake errors, 16 5xx,
  4 connection resets, 2 404). The two 404s are a server that rejects the
  checker's user agent (`dnsviahttp.com`, 200 in a browser) and a duplicate
  `OpenFEC` row that is now merged into `FEC OpenFEC`.
- 19 stale canonical links updated, 5 rebrand moves applied, 7 dead or duplicate
  rows removed (`Papers with Code` and `HubSpot Visitor Identification` had
  collapsed into other products, `Shibe.Online` and the ACNH API are parked
  domains, `Item API` and `BatchService` were marketplace leftovers, `OpenFEC`
  duplicated `FEC OpenFEC`), and `host-t.com` renamed to `DNS via HTTP`.
- `linkcheck` no longer sends a `Range` header: some servers answer it with 400 or
  404, which produced false failures on live sites.
- Remaining failures are gated, bot-blocked or temporarily down and are listed in
  `reports/maintenance-<date>.md`, not removed.

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
