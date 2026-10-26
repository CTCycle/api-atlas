# Competitive comparison

How API Atlas differs from the directories it is most often compared with.
This is a feature comparison, not a claim of superiority on every axis.

## Reference repositories

| Repository | Shape | Entries | Metadata | Tooling | Licence notes |
| --- | --- | --- | --- | --- | --- |
| public-apis/public-apis | Single `README.md`, one table per category | ~1,500 APIs | API, Description, Auth, HTTPS, CORS | format.py, links.py, unittest, 3 workflows | MIT code; sponsored APILayer block |
| brandonhimpfen/awesome-apis | Single `README.md`, curated links | ~hundreds | Name + one-line blurb | None | Mixed (APIs, SDKs, tools, courses) |
| Kikobeats/awesome-api | Single `README.md` | ~hundreds | Name + blurb | None | Resources for designing APIs, not a data catalog |
| github.com/topics/public-api | Topic index | n/a | n/a | GitHub search | Discovery only |

## Where API Atlas is different

1. **Richer, honest metadata.** Nine columns: Name, Type, Description, Access,
   Auth, License, Docs, Source, Checked. Pricing and access are recorded as stated
   by the provider, with `-` for anything unconfirmed. Competitors record auth
   and HTTPS/CORS only.
2. **More resource types.** APIs, Datasets, Portals and MCP servers share one
   schema, so an AI agent or researcher can find data sources, not only REST
   endpoints.
3. **Provenance per row.** The Source column records whether a row is `editorial`,
   `public-apis`, `APIs.guru` or `awesome-datasets`, and Checked records when a
   person last read the official documentation. Nothing is presented as verified
   that was not.
4. **Separated category files.** One file per category, so a pull request touches
   one small file and reviewers see a small diff. No 2,700-line README.
5. **No sponsored content.** There are no ad slots, featured placements or
   affiliate links. Rows are sorted alphabetically and validated in CI.
6. **Safety-first maintenance.** The script never edits the catalog. Link checks
   produce a report; removal requires a human decision and evidence. Transient
   failures never delete a row.
7. **Stdlib only.** `scripts/catalog.py` uses the Python standard library, so
   validation runs on a clean machine with Python 3.10+.
8. **Machine-readable copy kept in sync.** `data/catalog.jsonl` and
   `data/catalog.csv` are generated and checked in CI for freshness.
9. **Unit tests.** `tests/test_catalog.py` covers parsing, values, ordering and
   duplicate detection, matching the public-apis approach.

## What we deliberately did not adopt

- A single README (rejected: reviewability).
- Minimum entries per category (rejected: invites padding).
- Automatic rewriting of the catalog by importers (rejected: accuracy).
- Cloud service enumerations (rejected: noise).
