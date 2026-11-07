# Public release checklist

The repository is private until the flip described below, so this list is the gate.
Content and community items can be done at any time; the settings GitHub only
exposes on public repositories (branch protection, private vulnerability reporting)
and the version tag happen at or after the flip, in the order given.

Last reviewed 2026-11-07, in the pre-release audit.

## Content

- [x] `python scripts/catalog.py validate` returns 0 errors.
- [x] `python scripts/catalog.py export --format jsonl`, `--format json` and
      `--format csv` are run and committed, `shortlist` regenerated, and CI's
      freshness check passes.
- [x] Full verification completed within the last 30 days:
      `python scripts/catalog.py verify`, then `python scripts/catalog.py triage`.
      2,873 URLs checked on 2026-11-07, after the last row edit: 2,640
      answered, 43 moved, 100 gated, 42 timeouts, 22 transport errors, 16 TLS
      errors, 5 unreachable, 1 DNS failure and 1 broken link.
- [x] Every row in the `remove-or-replace`, `retired` and `confirm-new-domain`
      buckets is fixed or accepted with a note in the pull request. AgentPay Doc
      Tools and Covid-19 Datenhub answered a browser GET and a third-party reader,
      so the local 404/DNS result was not treated as death; Cep.la was removed;
      LAPIS was repointed to cov-spectrum.org; the deprecated Tripadvisor Content
      API row was replaced by Terra. The single `auth-mismatch` row (UNIDO) sits
      behind a Cloudflare challenge, not an API key.
- [x] `python scripts/probe.py --missing --index data/openapi-index.json` run, so
      the published spec index matches the catalog: 528 of 2,092 API rows.
- [x] No category file is a placeholder. Empty categories either have content or do
      not exist in `CATEGORIES`.
- [x] Counts quoted in README and CHANGELOG match `stats` output: 2,520 rows.
- [x] No duplicate rows: `python scripts/catalog.py duplicates` reports no shared
      URL or name group, and every exported `id` is unique.

## Cross-reference against upstream collections

- [x] public-apis/public-apis, awesomedata/awesome-public-datasets,
      APIs-guru/openapi-directory and punkpeye/awesome-mcp-servers fetched on
      2026-11-07 and compared by URL, path and provider host.
- [x] Every candidate that passed the scope filters was probed before it was
      added; 10 rows were accepted and the rest recorded as dead, parked, gated or
      out of scope.
- [x] The coverage numbers and the reason for the remaining gap are published in
      `docs/comparison.md`.

## Legal and attribution

- [x] `LICENSE` (MIT) names the right copyright holder.
- [x] `ATTRIBUTION.md` lists every upstream catalog actually used, with its licence.
- [x] The MIT notice covers the code, and the compilation licence (CC BY 4.0) is
      stated separately and clearly.
- [x] Rows derived from upstream keep their Source value.
- [x] No copied text that is not covered by an upstream licence.
- [x] Trademark names are used descriptively only.
- [x] `CODE_OF_CONDUCT.md` and `SECURITY.md` are present and linked from README and
      CONTRIBUTING.

## Repository settings (before the flip)

- [x] Description: "A curated Markdown directory of APIs, datasets, open-data
      portals and MCP servers, with provenance and verification dates."
- [x] Topics: `api`, `apis`, `datasets`, `open-data`, `developer-tools`,
      `awesome-list`, `mcp`, `catalog`, `reference`, `markdown`.
- [x] Issues enabled; blank issues disabled so the two forms are used.
- [x] `suggestion` and `correction` labels exist, so the issue forms apply them.
- [x] Wiki and projects disabled unless they are maintained.
- [x] Stale branches deleted. `develop` and `catalog-v2` were fully merged and
      removed on 2026-11-03; only `main` remains.
- [ ] Social preview image set (optional).

## Security and hygiene

- [x] `git log -p` searched for keys, tokens and internal paths.
- [x] No personal email addresses in commits that should not be public.
- [x] `.gitignore` covers `reports/` and local scratch directories.
- [x] Dependencies: none beyond the Python standard library for the catalog tools.
      Verify `python scripts/catalog.py validate` runs on a clean machine.

## At the flip

- [x] Flip visibility to public. Done on 2026-11-07 from the merge commit of the
      release pull request.
- [x] Enable private vulnerability reporting (Security settings), then confirm the
      links in `SECURITY.md` and `CODE_OF_CONDUCT.md` resolve.
- [x] Protect `main`: the `validate` and `tests` checks are required, force pushes
      and branch deletion are blocked.

## After the flip

- [x] Create the `v2.0.0` release from the merge commit, with the CHANGELOG section
      as the notes. Published 2026-11-07.
- [x] Check the README badges and relative links render on the public repository.
      Verified 2026-11-07: the validate badge, the CC BY badge and the raw
      `catalog.jsonl` all answer 200.
- [ ] Watch issues for the first week, especially correction reports.
- [ ] Re-run the maintenance report monthly.
- [ ] Decide on the optional schedule only after the first two manual runs behaved
      as expected.
- [ ] Add the repository to relevant awesome lists only if asked, not as spam.
