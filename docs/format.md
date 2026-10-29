# Catalog format

The catalog is plain Markdown. One file per category in `catalog/`, each holding a
single table. Those tables are the source of truth: edit them directly in the
GitHub web editor or in your local clone. Nothing is generated from a database and
no build step is required to contribute.

## Columns

| Column | Meaning | Allowed values |
| --- | --- | --- |
| Name | Link to the resource's official website. If no website exists, link to its documentation or repository. | Markdown link to an `http(s)` URL |
| Type | What kind of resource it is. | `API`, `Dataset`, `Portal`, `MCP` |
| Description | One factual sentence, 40 to 200 characters. No marketing language, no trailing period. | free text |
| Access | The cheapest usable tier, as stated by the provider or the upstream listing. | `Free`, `Free tier`, `Freemium`, `Paid`, `Restricted`, `-` |
| Auth | What you need before the first request. | `None`, `API key`, `OAuth`, `Registration`, `Account`, `-` |
| License | Licence or terms that govern use of the data or API. Link it when the provider publishes a licence page. | text or Markdown link, `-` |
| Docs | Direct link to official documentation. | Markdown link, `-` |
| Source | Where the row came from. | `editorial`, `public-apis`, `APIs.guru`, `awesome-datasets`, or a comma separated combination |
| Checked | Date someone last read the official documentation and confirmed the row. | `YYYY-MM-DD`, `-` |

`-` means "not established". It is never a placeholder for "probably free" or
"probably open". A dash in Access means the pricing model is unknown, not that the
resource is closed.

### Access values

- `Free`: no payment required, including for commercial use within the stated terms.
- `Free tier`: a free allowance exists with limits; paid plans may be needed above it.
- `Freemium`: free and paid plans coexist, with the free plan limited in scope.
- `Paid`: payment is required, even for a trial.
- `Restricted`: access is gated by approval, an institution, a licence agreement or
  a legal basis (research access, credentials, NDA).
- `-`: not established.

### Auth values

- `None`: no credentials required.
- `API key`: a key or token issued by the provider.
- `OAuth`: delegated authorisation flow.
- `Registration`: a free account, no key required for reads.
- `Account`: a paid or approved account is required.

### Source values

- `editorial`: written or rewritten by a maintainer, usually with a Checked date.
- `public-apis`: carried over from [public-apis/public-apis](https://github.com/public-apis/public-apis) (MIT).
- `APIs.guru`: carried over from the [APIs.guru openapi-directory](https://github.com/APIs-guru/openapi-directory) (CC0-1.0).
- `awesome-datasets`: carried over from [awesomedata/awesome-public-datasets](https://github.com/awesomedata/awesome-public-datasets) (MIT).

Source describes the origin of the row, not the quality of the resource. A row
with no Checked date is an unverified pointer: the link worked at some point, the
metadata may have changed since.

## File layout

```text
catalog/
  ai-ml.md
  geospatial.md
  ...
  mcp-servers.md
```

Each file starts with an H1 title, one line of scope, then the table. Rows are
sorted by name, case-insensitively. The first table row must be the header shown
above, followed by the divider row.

## Editing rules

1. One resource per row. Do not add a row for a sub-endpoint of an existing resource.
2. Link the canonical page, not a redirect, not an affiliate link, not a search result.
3. If you cannot confirm a value, write `-`. Do not guess.
4. Keep descriptions to one sentence. Say what the resource contains, not why it is great.
5. Put a resource in the category a reader would look in, not the one the provider uses.
6. Do not reorder rows by hand. The validator enforces alphabetical order.

## Machine-readable copy

`data/catalog.jsonl`, `data/catalog.json` and `data/catalog.csv` are generated from
the Markdown with:

```bash
python scripts/catalog.py export --format jsonl   # one object per line
python scripts/catalog.py export --format json     # one array
python scripts/catalog.py export --format csv
```

They exist for scripts and agents. If they disagree with the Markdown, the Markdown
wins. `validate` checks that the committed JSONL still matches the tables field for
field, and CI runs the same check.

### Fields

The nine table columns become nine fields (`name`, `type`, `category`,
`description`, `website`, `docs`, `access`, `auth`, `license`, `source`, `checked`,
where `docs` and `checked` are `null` when the table shows `-`), plus:

| Field | Meaning |
| --- | --- |
| `id` | Stable identifier: resource host without `www`, plus the slugified name |
| `verified` | `true` when `checked` is set: a person confirmed the row at least once |
| `docs_present` | `true` when a documentation URL is recorded |
| `license_known` | `true` when a licence or terms value is recorded |

The three derived fields are booleans on purpose. They never change because a day
passed, so the committed export stays stable between regenerations and the CI
freshness check keeps meaning something. Whether a row is *current* is a judgement
for the reader: compare `checked` with today.

`data/catalog.schema.json` describes the same records as JSON Schema 2020-12, with
the allowed values for `type`, `access`, `auth` and `source`.
