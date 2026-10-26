# Public release checklist

The repository is private. Work through this list before making it public, and
tick items in the pull request description.

## Content

- [ ] `python scripts/catalog.py validate` returns 0 errors.
- [ ] `python scripts/catalog.py export --format jsonl` and `--format csv` are run
      and committed, and CI's freshness check passes.
- [ ] Full link check completed within the last 30 days.
      `python scripts/catalog.py linkcheck` then `python scripts/catalog.py report`.
- [ ] Broken and redirected rows from the report are either fixed or accepted with
      a note in the pull request.
- [ ] No category file is a placeholder. Empty categories either have content or
      do not exist in `CATEGORIES`.
- [ ] Counts quoted in README and CHANGELOG match `stats` output.

## Legal and attribution

- [ ] `LICENSE` (MIT) names the right copyright holder.
- [ ] `ATTRIBUTION.md` lists every upstream catalog actually used, with its licence.
- [ ] The MIT notice covers the code, and the compilation licence (CC BY 4.0) is
      stated separately and clearly.
- [ ] Rows derived from upstream keep their Source value.
- [ ] No copied text that is not covered by an upstream licence.
- [ ] Trademark names are used descriptively only.

## Repository settings

- [ ] Description: "A curated Markdown directory of APIs, datasets, open-data
      portals and MCP servers, with provenance and verification dates."
- [ ] Topics: `api`, `apis`, `datasets`, `open-data`, `developer-tools`,
      `awesome-list`, `mcp`, `catalog`, `reference`, `markdown`.
- [ ] Default branch protected, validate workflow required.
- [ ] Issues enabled, blank issues disabled so the two forms are used.
- [ ] Wiki and projects disabled unless they are maintained.
- [ ] Social preview image set (optional).
- [ ] Release tag `v2.0.0` created after the public flip, not before.

## Security and hygiene

- [ ] `git log -p` searched for keys, tokens and internal paths.
- [ ] No personal email addresses in commits that should not be public.
- [ ] `.gitignore` covers `reports/` and local scratch directories.
- [ ] Dependencies: none beyond the Python standard library. Verify
      `python scripts/catalog.py validate` runs on a clean machine.

## After publishing

- [ ] Watch issues for the first week, especially correction reports.
- [ ] Re-run the maintenance report monthly.
- [ ] Decide on the optional Hermes schedule only after the first two manual runs
      behaved as expected.
- [ ] Add the repository to relevant awesome lists only if asked, not as spam.
