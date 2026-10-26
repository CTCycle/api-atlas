# Inclusion and exclusion criteria

The catalog is curated. Size is not a goal. A resource earns a row by being
usable, documented and distinct.

## What belongs

1. **A real access surface.** An HTTP API, a downloadable dataset, a data portal
   with a catalog, or an MCP server. The landing page must be reachable and the
   documentation must describe how to start.
2. **Self-serve or clearly described access.** Free, free tier, pay-per-use with
   published pricing, or a restricted source whose access route is documented
   (application form, institutional licence, credentials). Enterprise-only
   resources are included only when the documentation is public and the resource
   is otherwise notable.
3. **A stable canonical URL.** The official site, repository or portal. Not a
   search result, not a mirror, not an affiliate link, not a redirect chain.
4. **A distinct resource.** If a row already covers the provider's platform, do
   not add rows for individual endpoints, regions or plan tiers.
5. **Enough metadata to be useful.** Name, one factual sentence, a working link
   and a plausible category. Everything else may be `-`.

## What does not belong

- **Libraries, SDKs, frameworks and tools** that are not themselves an API, data
  source or MCP server.
- **Enumerations of cloud platform services.** One row for the platform, not 250
  rows for its individual APIs. Bulk service lists are noise in a discovery
  catalog.
- **Dead resources.** A 404 or a retired domain is a removal candidate after one
  confirmation.
- **Aggregator landing pages.** A row that resolves to `rapidapi.com` or a similar
  marketplace root does not help anyone; link the provider or skip it.
- **Scraping endpoints presented as APIs.** Undocumented internal endpoints, or
  endpoints whose terms forbid the use they are listed for.
- **Abandoned projects** with no release, commit or working endpoint in the last
  two years, unless they are the canonical archive for a dataset.
- **Duplicates.** The same resource under two names, two domains or two categories.
- **Marketing claims.** Superlatives, "best", "leading", "revolutionary".

## Classification rules

- Access is the cheapest usable tier, not the most expensive one.
- A free trial is not `Free`. Use `Paid` and mention the trial in the description
  only if it is material.
- `Restricted` is for approval-gated or legally gated access, not for "requires a
  free account". That is `Registration`.
- Licence is what the provider states for the data or the API, not what the
  upstream list guessed. If the provider publishes no licence, use `-`.
- Category is where a reader would look, not where the provider files itself.

## Provenance and attribution

Rows carried over from an upstream catalog keep their source in the Source column.
Upstream licences are recorded in [ATTRIBUTION.md](../ATTRIBUTION.md). When a row
is rewritten from scratch and verified, the source becomes `editorial` and the
Checked date is set.

## Removal

Removal requires evidence: a confirmed 404 or 410, a retired domain, a documented
shutdown notice, or a duplicate merge. Transient failures, bot blocking, TLS
errors and timeouts are never grounds for removal on their own. See
[maintenance.md](maintenance.md).
