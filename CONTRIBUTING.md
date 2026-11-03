# Contributing

Thanks for helping. This catalog is small on purpose: a row is added when someone
has checked that the resource exists, is documented and is not already listed.

## The fast path

Every category page has an **Edit** link in the GitHub file view. Add one row in
alphabetical position and open a pull request. That is the whole workflow.

```markdown
| [Open-Meteo](https://open-meteo.com/) | API | Weather forecasts, historical reanalysis and climate projections for any coordinate | Freemium | None | [CC BY 4.0](https://open-meteo.com/en/license) | [docs](https://open-meteo.com/en/docs) | editorial | 2026-10-24 |
```

Column meanings, allowed values and the exact row format are in
[docs/format.md](docs/format.md).

## Before you open the pull request

```bash
python scripts/catalog.py validate
python scripts/catalog.py export --format jsonl
```

No dependencies are needed beyond Python 3.10. `validate` checks the table shape,
the allowed values, alphabetical order and the README navigation. `export`
refreshes `data/catalog.jsonl`; CI fails if it is out of date.

## What gets merged

- A working canonical link, plus a documentation link when one exists.
- A description that says what the resource contains, in one sentence.
- Honest values. `-` is a valid answer for anything you could not confirm.
- `Checked` set to the date you actually read the provider's documentation. Do not
  set it because a script returned HTTP 200.

## What gets rejected

- Marketing copy, superlatives, keyword stuffing.
- Affiliate, referral or tracking links.
- A second row for an endpoint, region or plan of a resource that is already listed.
- Individual services of a large cloud platform. One row for the platform is enough.
- Dead resources and projects that have not shipped anything in two years.
- Rows with invented pricing, licence or auth values.

The full policy is in [docs/inclusion-criteria.md](docs/inclusion-criteria.md).

## Removing or correcting a row

Open an issue with the row name and the evidence: the URL you tried, the status
code, the provider notice, or the page that contradicts the row. Corrections from
providers take priority.

If you are the operator of a listed resource and want it changed or removed, say so
in the issue and it will be handled without argument.

## Suggesting without a pull request

Use the [add a resource](https://github.com/CTCycle/api-atlas/issues/new?template=add-resource.yml)
issue form. A maintainer will do the row formatting. Suggestions are not applied
automatically.

## Code of Conduct

Participation in this project is covered by the [Code of Conduct](CODE_OF_CONDUCT.md).
Reports are handled privately. Security problems follow [SECURITY.md](SECURITY.md)
instead of the public issue tracker.

## Style

- British spelling in prose, but keep the provider's own spelling for names.
- No em dashes.
- One sentence per description, no trailing period.
- Categories are listed in `scripts/catalog.py` and mirrored in the README. Adding
  a category needs both, plus a `catalog/<slug>.md` file.
