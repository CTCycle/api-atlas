# Attribution

This project is a derivative compilation. It does not copy upstream catalogs verbatim. Each record links back to its upstream entry where an upstream id exists, and per record provenance carries the source name, source URL, source licence, upstream id, import date and source version.

## Code

- Licence: MIT
- Scope: everything under `regipy/`, `scripts/`, `tests/` and the tooling in `.github/`.

## Catalog data

- Licence for original compilation: Creative Commons Attribution 4.0 International (CC BY 4.0).
- Scope: field normalisation, categorisation, verification metadata and any editorial additions.
- Records derived from an upstream source keep that upstream licence. The upstream licence string is stored in `provenance[].source_license`.

## Upstream: public-apis/public-apis

- What was used: API entries, descriptions, categories, authentication and HTTPS information.
- Repository: https://github.com/public-apis/public-apis
- Upstream licence: MIT
- Attribution line: public-apis/public-apis, MIT licence.
- Redistribution obligations: retain the MIT copyright notice and permission notice in any redistribution of the upstream material. The MIT licence requires the notice to be included in all copies or substantial portions.

## Upstream: APIs.guru openapi-directory

- What was used: API metadata, OpenAPI specification links, categories and provider information.
- Repository: https://github.com/APIs-guru/openapi-directory
- Upstream licence: CC0 1.0 Universal
- Attribution line: APIs.guru openapi-directory, CC0 1.0.
- Redistribution obligations: none required by CC0. Attribution is appreciated but not legally required. The data is dedicated to the public domain.

## Upstream: awesomedata/awesome-public-datasets

- What was used: dataset entries, descriptions, source links and topic sections.
- Repository: https://github.com/awesomedata/awesome-public-datasets
- Upstream licence: MIT
- Attribution line: awesomedata/awesome-public-datasets, MIT licence.
- Redistribution obligations: retain the MIT copyright notice and permission notice in any redistribution of the upstream material.

## Provider policies

Provider level licence rules in `schema/provider-policies.yaml` are derived from the published terms of the named providers. Each rule cites the page that states the terms. These are not guesses.

## Contact and corrections

If an upstream project or provider believes a record misrepresents its terms, open an issue or use `python -m regipy.cli flag <entry-id>` so the record is reviewed.