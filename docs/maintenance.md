# Maintenance

The catalog is maintained by hand with one optional helper script. There is no
crawler, no scheduler requirement and no database. Everything below works with a
plain clone and Python 3.10 or newer, with no third-party packages.

```bash
python scripts/catalog.py validate      # structure, values, order, navigation, export agreement
python scripts/catalog.py stats         # counts by category, type, access and source
python scripts/catalog.py linkcheck     # HTTP check every website and docs URL
python scripts/catalog.py verify        # linkcheck plus final URL, page title, retirement wording
python scripts/catalog.py triage        # turn the newest verify report into a decision queue
python scripts/catalog.py report        # build reports/maintenance-YYYY-MM-DD.md
python scripts/catalog.py duplicates    # shared URLs, same name on one domain
python scripts/catalog.py stale         # entries with old or missing Checked dates
python scripts/catalog.py shortlist     # regenerate docs/no-auth.md
python scripts/catalog.py export        # data/catalog.jsonl, data/catalog.json and data/catalog.csv
python scripts/probe.py                 # discover live OpenAPI/Swagger specs for API rows
python scripts/probe.py --missing --index data/openapi-index.json
                                        # probe only rows with no known spec, refresh the index
```

The script never edits `catalog/`. It writes JSON and Markdown under `reports/`.
Applying a proposed change is a human decision, made with a normal commit. The only
files it rewrites are the derived artifacts (`data/`, `docs/no-auth.md`), and CI
fails when those are stale.

## Routine

**Every pull request**

```bash
python scripts/catalog.py validate
python scripts/catalog.py export --format jsonl
```

CI runs the same validation and fails when `data/catalog.jsonl` is stale.

**Monthly, 20 to 30 minutes**

```bash
python scripts/catalog.py linkcheck --limit 300     # rotating sample
python scripts/catalog.py report
python scripts/catalog.py stale --days 365
```

Read `reports/maintenance-<date>.md` and act on the categories below.

**Quarterly, one to two hours**

```bash
python scripts/catalog.py linkcheck                 # full sweep
python scripts/catalog.py report
python scripts/catalog.py duplicates
```

A full sweep is roughly 3,500 requests at 8 workers with a one request per second
per host limit. Expect 15 to 30 minutes.

## Triage rules

| Result | Meaning | Action |
| --- | --- | --- |
| 200 to 299 | Reachable | Nothing |
| Moved, same domain | New canonical path | Update the link to `final_url`, then re-check |
| Moved, different domain | Rebrand, acquisition or hijack | Open it in a browser, confirm the service is the same, then update or remove |
| Parked or expired | Domain for sale or lapsed | Remove |
| 401, 402, 403, 429, 451 | Gated or rate limited | Keep the row. Record the auth requirement if it changed |
| 404, 410 | Gone | Confirm in a browser, then fix the link or remove the row |
| DNS failure | Domain retired | Confirm, then remove |
| TLS error | Often bot protection | Re-check in a browser before acting |
| TLS chain incomplete | The server's certificate chain does not validate in this client, a browser completes it | No action; the row is fine |
| Timeout, 5xx, transport error | Usually transient | Re-run the check. Remove only after a second failure on a different day |
| Retirement wording on the page | Provider announced a shutdown | Remove, or mark the successor |
| Gated but `Auth` says `None` | The row is wrong about access | Read the docs and fix the Auth value |

Two rules override everything else:

1. Never remove a row because of a single automated failure.
2. Never overwrite a verified description, licence or access value from a link
   check. A link check can only prove that a URL answered.

## What each check can and cannot prove

- `validate` proves the table shape, the allowed values, alphabetical order,
  category coverage, README navigation, and that the committed export matches the
  tables field for field. It proves nothing about truth.
- `linkcheck` proves that a URL answered with a status code, following redirects to
  the real destination. It does not prove the page still describes the same service,
  that pricing is unchanged, or that access works behind a login.
- `verify` adds the final URL, the page title and the presence of retirement or
  parking wording. It still cannot read pricing out of a page that renders with
  JavaScript.
- `triage` groups the newest verify report by the decision each row needs. It is a
  work queue, not a verdict.
- `probe` proves that a provider publishes an OpenAPI or Swagger document that
  parses and has paths. That is the strongest evidence available without a key; it
  does not prove every endpoint responds.
- `duplicates` proves that two rows share a URL or a name on a domain. It does not
  prove they describe the same real service.
- `stale` proves that nobody has confirmed a row recently. It does not prove the
  row is wrong.

Pricing, rate limits and licence terms are only ever confirmed by reading the
provider's page. That is why the Checked column exists and why it is set by a
person, not by the script.

## Optional scheduling with Hermes

Hermes can run the same commands on a schedule and deliver the report. Nothing is
merged or deleted automatically. The proposal below is not active; enable it only
after reviewing the commands and the destination.

```text
name:     api-atlas monthly link check
schedule: 1st of the month, 06:00 local
command:  cd <repo> && python scripts/catalog.py linkcheck && python scripts/catalog.py report
output:   reports/maintenance-<date>.md delivered as a message summary
review:   open the report, apply the diff blocks by hand
```

A weekly bounded sample (`linkcheck --limit 150`) is enough between full sweeps if
the catalog grows past roughly 5,000 rows.

## Adding a resource

1. Find the canonical page and the documentation page.
2. Confirm what the resource is, who runs it, what it costs and what its terms say.
3. Add one row in the right category, in alphabetical position.
4. Set `Checked` to today only if you actually read the documentation.
5. Run `validate` and `export`, then open a pull request.

## Repository settings that matter

- Keep the default branch protected and require the validate workflow.
- Keep `data/catalog.jsonl` committed so agents and scripts can fetch one file.
- Do not add a hosted service, a database or a web frontend. GitHub renders the
  catalog and search works through the repository search box.
