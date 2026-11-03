# Security policy

This repository is a catalog and a set of small standard-library Python tools. It
does not run a hosted service, accept credentials or process data from visitors. The
realistic security issues are therefore limited, but they still matter:

- a link in the catalog that leads to malware, a typosquat or a phishing page
- an entry that misrepresents a paid service as free, or a provider's terms
- a vulnerability in `scripts/` when the tools are pointed at untrusted URLs
- a leaked secret in the repository history

## Reporting

Do not open a public issue for a security problem. Use GitHub's private reporting on
this repository: **Security → Advisories → Report a vulnerability**. That channel is
visible only to the maintainer.

Include the URL or file affected, what you observed, and how to reproduce it. If the
report is about a listed third-party resource, say so and, when possible, whether the
provider is aware.

## What to expect

- Acknowledgement within seven days.
- Removal or correction of an affected catalog row as soon as it is confirmed, with
  the reason recorded in the pull request.
- A fix or a documented mitigation for a tooling issue. There is no bug bounty.
- Credit in the advisory if you want it, or anonymity if you prefer.

## Supported versions

The catalog is served from the default branch, `main`. There are no maintained
release branches, so fixes land on `main` and the generated exports are refreshed in
the same pull request.
