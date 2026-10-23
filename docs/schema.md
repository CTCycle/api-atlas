# Schema reference

This document describes every field of a registry record. The machine readable definition is `schema/entry.schema.json`. Unknown values must be `null` or `unknown`, never invented.

## Top level fields

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| id | string | pattern `^[a-z0-9][a-z0-9.-]*(/[a-z0-9][a-z0-9._-]*)?$` | Stable identifier, usually provider domain plus resource slug. |
| kind | string | `api`, `dataset` | Whether the entry is an API or a dataset. |
| name | string | 1 to 200 characters | Display name of the API or dataset. |
| description | string or null | up to 1200 characters | Short factual description. |
| category | string | any key in `schema/taxonomy.yaml` categories | Primary category. Falls back to `unknown`. |
| tags | array of string | lowercase slug pattern, unique | Secondary domains or keywords. |
| type | string | `rest`, `graphql`, `openapi`, `feed`, `unknown` for APIs; `dataset`, `download`, `database`, `portal`, `unknown` for datasets | Resource type. |
| provider | object | see below | Provider identity. |
| urls | object | see below | Links to the resource. |
| access | object | see below | How the resource is accessed. |
| technical | object | see below | Technical details. |
| pricing | object | see below | Cost and free tier information. |
| license | object | see below | Licence and commercial use. |
| coverage | object | see below | Geographic and temporal coverage. |
| formats | array of string | unique | Data formats, for example `csv`, `json`, `parquet`. |
| update_frequency | string | `realtime`, `hourly`, `daily`, `weekly`, `monthly`, `periodic`, `static`, `unknown` | How often the data updates. |
| status | string | `active`, `deprecated`, `unavailable`, `unverified` | Current availability. |
| verification | object | see below | Verification state. |
| curation | object | see below | Curation level. |
| provenance | array of object | at least one item, see below | Upstream sources. |
| aliases | array of string | | Alternative identifiers produced by merges. |
| conflicts | array of object | see below | Recorded disagreements during merges. |
| flags | array of object | see below | User or maintainer flags. |
| notes | string or null | up to 1200 characters | Free form notes. |

## provider

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| id | string | | Provider identifier, often a domain. |
| name | string | | Provider display name. |
| domain | string or null | | Registrable domain used for policy matching. |

## urls

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| website | string or null | URI | Main website or landing page. |
| documentation | string or null | URI | Documentation URL. |
| spec | string or null | URI | Machine readable specification URL. |
| signup | string or null | URI | Registration or API key signup URL. |
| terms | string or null | URI | Terms of service or licence URL. |

## access

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| model | string | `public`, `api_key`, `oauth`, `registration`, `restricted`, `unknown` | Access model. |
| notes | string or null | up to 600 characters | Access notes, for example rate limits or registration steps. |

## technical

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| https | boolean or null | | Whether HTTPS is supported. |
| cors | string | `yes`, `no`, `unknown` | Cross origin resource sharing support. |
| auth_schemes | array of string | | Authentication schemes, for example `ApiKey`, `OAuth2`. |

## pricing

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| model | string | `free`, `freemium`, `paid`, `unknown` | Pricing model. |
| free_tier_indicated | boolean or null | | Whether a free tier is advertised. |
| free_tier_limits | string or null | up to 400 characters | Limits of the free tier. |
| basis | string or null | `upstream_catalog`, `official_docs`, `manual`, null | Evidence source for pricing. |
| notes | string or null | up to 400 characters | Pricing notes. |

## license

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| name | string or null | | Licence name. Required as evidence for any commercial use claim. |
| spdx | string or null | | SPDX identifier when known. |
| url | string or null | URI | Licence URL. |
| commercial_use | string | `allowed`, `restricted`, `prohibited`, `unknown` | Whether commercial use is allowed. |
| attribution_required | boolean or null | | Whether attribution is required. |
| basis | string or null | `provider_policy`, `official_docs`, `manual`, null | Evidence source for the licence. |
| notes | string or null | up to 400 characters | Licence notes. |

## coverage

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| geographic | string or null | up to 200 characters | Geographic coverage. |
| temporal | string or null | up to 200 characters | Temporal coverage. |

## verification

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| last_verified | string or null | ISO date `YYYY-MM-DD` | Date key metadata was confirmed. |
| last_checked | string or null | ISO date `YYYY-MM-DD` | Date the URL or endpoint was last checked. |
| method | string | `none`, `upstream_import`, `http_head`, `manual_review` | How verification was performed. |
| confidence | string | `imported`, `partial`, `verified` | Verification tier. |
| http_status | integer or null | | HTTP status from the last check. |
| notes | string or null | up to 400 characters | Verification notes. |

## curation

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| level | string | `imported`, `curated` | Whether the record has been hand curated. |
| updated | string or null | ISO date `YYYY-MM-DD` | Date the curation level was last set. |

## provenance item

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| source | string | | Upstream source name, for example `public-apis`. |
| source_url | string or null | | URL of the upstream entry. |
| source_license | string or null | | Upstream licence. |
| upstream_id | string or null | | Identifier in the upstream catalog. |
| imported_at | string or null | ISO date `YYYY-MM-DD` | Import date. |
| source_version | string or null | | Upstream version or snapshot date. |

## conflicts item

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| field | string | | Dotted field path that disagreed. |
| kept | any | | Value that was kept. |
| discarded | any | | Value that was discarded. |
| discarded_source | string or null | | Source of the discarded value. |

## flags item

| Field | Type | Allowed values | Meaning |
| --- | --- | --- | --- |
| date | string | ISO date `YYYY-MM-DD` | Date the flag was raised. |
| reason | string | | Reason for the flag. |
| reporter | string or null | | Who raised the flag. |

## Example record

```json
{
  "id": "noaa.gov/noaa-climate-data-online",
  "kind": "dataset",
  "name": "NOAA Climate Data Online",
  "description": "Historical weather and climate observations from NOAA stations worldwide.",
  "category": "weather-climate",
  "tags": ["climate", "weather", "historical"],
  "type": "portal",
  "provider": {
    "id": "noaa.gov",
    "name": "National Oceanic and Atmospheric Administration",
    "domain": "noaa.gov"
  },
  "urls": {
    "website": "https://www.ncei.noaa.gov/cdo-web/",
    "documentation": "https://www.ncei.noaa.gov/cdo-web/webservices/v2",
    "spec": null,
    "signup": "https://www.ncei.noaa.gov/cdo-web/token",
    "terms": "https://www.noaa.gov/information-technology/open-data-dissemination"
  },
  "access": {
    "model": "api_key",
    "notes": "Free API token required for dataset downloads."
  },
  "technical": {
    "https": true,
    "cors": "unknown",
    "auth_schemes": ["ApiKey"]
  },
  "pricing": {
    "model": "free",
    "free_tier_indicated": true,
    "free_tier_limits": null,
    "basis": "official_docs",
    "notes": null
  },
  "license": {
    "name": "US Government work, public domain",
    "spdx": "PD-USGov",
    "url": "https://www.noaa.gov/information-technology/open-data-dissemination",
    "commercial_use": "allowed",
    "attribution_required": false,
    "basis": "provider_policy",
    "notes": null
  },
  "coverage": {
    "geographic": "Global",
    "temporal": "1763 to present"
  },
  "formats": ["csv", "json", "netcdf"],
  "update_frequency": "daily",
  "status": "active",
  "verification": {
    "last_verified": "2026-10-01",
    "last_checked": "2026-10-15",
    "method": "manual_review",
    "confidence": "verified",
    "http_status": 200,
    "notes": "Licence and access confirmed against NOAA documentation."
  },
  "curation": {
    "level": "curated",
    "updated": "2026-10-15"
  },
  "provenance": [
    {
      "source": "curated",
      "source_url": null,
      "source_license": null,
      "upstream_id": null,
      "imported_at": "2026-10-15",
      "source_version": null
    }
  ]
}
```

This example is illustrative. Real entries may omit optional fields and keep unknown values explicit.