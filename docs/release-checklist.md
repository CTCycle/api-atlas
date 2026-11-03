# Public release checklist

The repository is private until the flip described below, so this list is the gate.
Content and community items can be done at any time; the settings GitHub only
exposes on public repositories (branch protection, private vulnerability reporting)
and the version tag happen at or after the flip, in the order given.

## Content

- [ ] `python scripts/catalog.py validate` returns 0 errors.
- [ ] `python scripts/catalog.py export --format jsonl`, `--format json` and
      `--format csv` are run and committed, `shortlist` regenerated, and CI's
      freshness check passes.
- [ ] Full verification completed within the last 30 days:
      `python scripts/catalog.py verify`, then `python scripts/catalog.py triage`.
- [ ] Every row in the `remove-or-replace`, `retired` and `confirm-new-domain`
      buckets is fixed or accepted with a note in the pull request.
- [ ] `python scripts/probe.py --missing --index data/openapi-index.json` run, so
      the published spec index matches the catalog.
- [ ] No category file is a placeholder. Empty categories either have content or do
      not exist in `CATEGORIES`.
- [ ] Counts quoted in README and CHANGELOG match `stats` output.
- [ ] No duplicate rows: `python scripts/catalog.py duplicates` reports no shared
      URL or name group, and every exported `id` is unique.

## Legal and attribution

- [ ] `LICENSE` (MIT) names the right copyright holder.
- [ ] `ATTRIBUTION.md` lists every upstream catalog actually used, with its licence.
- [ ] The MIT notice covers the code, and the compilation licence (CC BY 4.0) is
      stated separately and clearly.
- [ ] Rows derived from upstream keep their Source value.
- [ ] No copied text that is not covered by an upstream licence.
- [ ] Trademark names are used descriptively only.
- [ ] `CODE_OF_CONDUCT.md` and `SECURITY.md` are present and linked from README and
      CONTRIBUTING.

## Repository settings (before the flip)

- [ ] Description: "A curated Markdown directory of APIs, datasets, open-data
      portals and MCP servers, with provenance and verification dates."
- [ ] Topics: `api`, `apis`, `datasets`, `open-data`, `developer-tools`,
      `awesome-list`, `mcp`, `catalog`, `reference`, `markdown`.
- [ ] Issues enabled; blank issues disabled so the two forms are used.
- [ ] `suggestion` and `correction` labels exist, so the issue forms apply them.
- [ ] Wiki and projects disabled unless they are maintained.
- [ ] Stale branches deleted (`develop` and `catalog-v2` are fully merged).
- [ ] Social preview image set (optional).

## Security and hygiene

- [ ] `git log -p` searched for keys, tokens and internal paths.
- [ ] No personal email addresses in commits that should not be public.
- [ ] `.gitignore` covers `reports/` and local scratch directories.
- [ ] Dependencies: none beyond the Python standard library for the catalog tools.
      Verify `python scripts/catalog.py validate` runs on a clean machine.

## At the flip

- [ ] Flip visibility to public.
- [ ] Enable private vulnerability reporting (Security settings), then confirm the
      links in `SECURITY.md` and `CODE_OF_CONDUCT.md` resolve. On a private
      repository on the free plan this feature is unavailable, which is why the
      check sits after the flip.
- [ ] Protect `main`: require the `validate` and `tests` checks, no force pushes,
      linear history optional. Branch protection also needs a public repository on
      the free plan.

## After the flip

- [ ] Create the `v2.0.0` release from the merge commit, with the CHANGELOG section
      as the notes.
- [ ] Check the README badges and relative links render on the public repository.
- [ ] Watch issues for the first week, especially correction reports.
- [ ] Re-run the maintenance report monthly.
- [ ] Decide on the optional Hermes schedule only after the first two manual runs
      behaved as expected.
- [ ] Add the repository to relevant awesome lists only if asked, not as spam.
