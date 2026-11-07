# Competitive comparison

How API Atlas differs from the directories it is most often compared with.
This is a feature comparison, not a claim of superiority on every axis.

## Reference repositories

Star counts and last push dates were read from the GitHub REST API on 2026-10-29.
Entry counts for other projects are the projects' own published figures or the
number of rows their list actually contains, not estimates.

| Repository | Shape | Scale | Metadata per row | Tooling | Licence notes |
| --- | --- | --- | --- | --- | --- |
| public-apis/public-apis | Single `README.md`, one table per category | 2,238 rows parsed from its README | API, Description, Auth, HTTPS, CORS | format.py, links.py, unittest, 3 workflows | MIT code; sponsored APILayer block inside the list |
| awesomedata/awesome-public-datasets | Topic list in `README.rst` | 1,118 entries parsed | Name, description, link | None | MIT; datasets keep their own licences |
| ripienaar/free-for-dev | Single `README.md` | hundreds of SaaS entries | Name, free-tier limits in prose | None | No licence column; free-tier claims go stale |
| APIs-guru/openapi-directory | OpenAPI documents plus a site | 2,529 API descriptions, 108,837 endpoints | Machine-readable specs only | Spec linter, weekly fixes | CC0-1.0; no pricing, no licence, no datasets |
| punkpeye/awesome-mcp-servers | MCP server list | thousands of servers | Name, description, install | None | MIT; transport and install detail is inconsistent |
| awesome-selfhosted/awesome-selfhosted | Table per section plus static site | hundreds of services | Licence, language, demo, Docker | CI, static site with search | Strong per-row licence metadata; software only |
| API Atlas | One Markdown table per category, 45 files | 2,520 rows (2,092 APIs, 285 portals, 76 datasets, 67 MCP) | Name, Type, Description, Access, Auth, License, Docs, Source, Checked | stdlib validator, verifier, triage, spec probe, JSON Schema, CI freshness | Code MIT, compilation CC BY 4.0, no sponsored rows |

## Where API Atlas is different

1. **Richer, honest metadata.** Nine columns: Name, Type, Description, Access,
   Auth, License, Docs, Source, Checked. Pricing and access are recorded as stated
   by the provider, with `-` for anything unconfirmed. Competitors record auth and
   HTTPS/CORS only, or nothing at all.
2. **More resource types.** APIs, datasets, portals and MCP servers share one
   schema, so a researcher or an agent can find data sources, not only REST
   endpoints. public-apis, awesome-public-datasets and the MCP lists each cover one
   type.
3. **Provenance per row.** `Source` records whether a row is `editorial`,
   `public-apis`, `APIs.guru` or `awesome-datasets`; `Checked` records when a person
   last read the official documentation. Nothing is presented as verified that was
   not.
4. **A verification pipeline, not a link check.** `verify` follows redirects to the
   real destination, records the page title, and detects parked domains, retirement
   notices and rows whose page no longer matches their name. `triage` turns that
   into a decision queue, including rows that answer 401/403 while claiming no auth.
   The 2026-11-07 pass covered 2,878 URLs, with redirects followed: 2,635
   answered, 57 moved, 92 gated, 43 timeouts, 23 transport errors, 16 TLS
   errors, 5 unreachable, 3 DNS failures, 1 broken link and 4 pages with
   retirement wording. Five duplicate rows were merged, 26 unreliable rows were
   deleted after the marketplace audit, and the dead domain Cep.la was removed.
5. **Machine-readable contracts, discovered not assumed.** `scripts/probe.py` looks
   for OpenAPI/Swagger documents on the website, in the docs page and at the
   conventional paths, and only counts a hit when the document parses and has
   paths. No other list of this kind tells you which of its entries publish a spec.
6. **A schema, not just a file.** `data/catalog.jsonl`, `data/catalog.json` and
   `data/catalog.csv` are generated from the Markdown, described by
   `data/catalog.schema.json` (JSON Schema 2020-12), and validated for agreement
   with the tables in CI. Derived booleans (`verified`, `docs_present`,
   `license_known`) let an agent filter without parsing dates.
7. **A shortlist for the impatient.** `docs/no-auth.md` is generated from the
   catalog and lists every free, keyless resource by category.
8. **Separated category files.** One file per category, so a pull request touches
   one small file and reviewers see a small diff. No 3,000-line README.
9. **No sponsored content.** No ad slots, featured placements or affiliate links.
   Rows are sorted alphabetically and validated in CI.
10. **Safety-first maintenance.** The tooling never edits the catalog. Link checks
    produce reports; removal requires a human decision and evidence, and a single
    automated failure never deletes a row.
11. **Stdlib only.** Every script runs on a clean machine with Python 3.10+ and no
    third-party packages.

## Coverage against upstream collections (2026-11-07)

The catalog was cross-checked against the four collections it draws from and
against the MCP list most often compared with it. An entry counts as represented
when its URL, path or provider host is already in the catalog.

| Upstream | Entries parsed | Already represented | Not represented |
| --- | --- | --- | --- |
| public-apis/public-apis | 2,343 | 1,810 | 533 |
| awesomedata/awesome-public-datasets | 1,153 | 240 | 913 |
| APIs-guru/openapi-directory | 2,529 | 96 | 2,433 |
| punkpeye/awesome-mcp-servers | 4,638 | 28 | 4,610 |

The gap is not the backlog. Of the 533 public-apis rows with no catalog entry,
238 failed the scope filters already written in `docs/inclusion-criteria.md`:
148 duplicated an existing provider name, 47 were marketplace or shared-platform
links, 23 offered no HTTPS endpoint and 20 sat in a sponsored APILayer section.
The remaining 295 were probed: 155 answered, 98 carried a page title that matched
their name, and 10 passed review and were added. The other 140 did not answer at
all, and most of the 88 live pages that were not added were parked domains,
resellers, gated landing pages or AI-generated sites with no documentation.

The same pattern holds for the other lists. awesome-mcp-servers is a directory of
4,638 repositories, most of them single-author servers; the catalog keeps 67 that
are official or widely used. APIs.guru describes 2,529 APIs but publishes no
pricing, licence or access model, and many are individual services of a cloud
platform, which the inclusion criteria exclude. awesome-public-datasets links
papers and Zenodo deposits as often as portals, and a dataset row needs a stable
canonical page before it can be listed.

Bulk imports are therefore not a coverage strategy. Each addition in this pass
was fetched, read and given a description, and the provenance stayed in the
`Source` column.

## What we deliberately did not adopt

- A single README (rejected: reviewability).
- Sponsored placements inside the list, as public-apis does (rejected: the catalog
  is not an ad surface).
- Minimum entries per category (rejected: invites padding).
- Automatic rewriting of the catalog by importers (rejected: accuracy).
- Cloud service enumerations (rejected: noise).
- Marketplace or aggregator root rows, such as a row that resolves to rapidapi.com
  (rejected: it does not help the reader).
