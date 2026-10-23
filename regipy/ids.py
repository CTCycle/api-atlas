"""Identifier and URL normalisation helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Iterable
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode

# Platforms that host many independent projects. For these the first path
# segment is part of the provider identity, otherwise thousands of unrelated
# entries would collapse onto "github.io".
HOSTING_DOMAINS = {
    "github.io",
    "netlify.app",
    "vercel.app",
    "herokuapp.com",
    "readthedocs.io",
    "readthedocs.org",
    "gitbook.io",
    "pages.dev",
    "web.app",
    "firebaseapp.com",
    "surge.sh",
    "glitch.me",
    "repl.co",
    "azurewebsites.net",
    "workers.dev",
    "fly.dev",
    "onrender.com",
    "blogspot.com",
    "wordpress.com",
    "notion.site",
    "s3.amazonaws.com",
    "storage.googleapis.com",
    "appspot.com",
    "pythonanywhere.com",
    "weebly.com",
    "wixsite.com",
    "carrd.co",
    "super.site",
}

# Minimal public suffix handling. Not a replacement for the real Public Suffix
# List, just enough to avoid treating "example.co.uk" as host "co.uk".
MULTI_PART_SUFFIXES = {
    "co.uk", "org.uk", "gov.uk", "ac.uk", "me.uk", "net.uk", "sch.uk",
    "co.jp", "or.jp", "ne.jp", "ac.jp", "go.jp",
    "com.au", "net.au", "org.au", "edu.au", "gov.au", "id.au",
    "co.nz", "net.nz", "org.nz", "govt.nz", "ac.nz",
    "co.in", "net.in", "org.in", "gov.in", "ac.in",
    "com.br", "net.br", "org.br", "gov.br", "edu.br",
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn",
    "com.mx", "org.mx", "gob.mx", "edu.mx",
    "com.tr", "org.tr", "gov.tr", "edu.tr",
    "com.ar", "org.ar", "gob.ar", "edu.ar",
    "co.za", "org.za", "gov.za", "ac.za",
    "com.sg", "edu.sg", "gov.sg",
    "co.kr", "or.kr", "go.kr",
    "com.tw", "org.tw", "gov.tw",
    "co.il", "org.il", "gov.il",
    "com.pl", "org.pl", "gov.pl",
    "com.ua", "org.ua", "gov.ua",
    "co.id", "or.id", "go.id",
    "com.my", "org.my", "gov.my",
    "com.hk", "org.hk", "gov.hk",
    "com.eg", "com.sa", "com.pk", "com.ng", "com.vn", "com.ph",
    "co.th", "in.th", "ac.th", "go.th",
    "gov.it", "edu.it", "org.it",
    "gouv.fr", "asso.fr", "com.fr",
    "gob.es", "org.es", "edu.es",
    "gov.nl", "ac.at", "gv.at", "co.at",
    "gov.ch", "admin.ch",
    "gov.ie", "gov.scot", "gov.wales",
}

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "utm_id", "utm_name", "ref", "referrer", "fbclid", "gclid", "mc_cid",
    "mc_eid", "source", "campaign",
}

SLUG_RE = re.compile(r"[^a-z0-9]+")


def _ascii_fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii")


def slugify(text: str, max_len: int = 56) -> str:
    """Turn a display name into a stable, ascii-only slug."""
    folded = _ascii_fold(text or "").lower()
    folded = folded.replace("&", " and ").replace("%", " percent ")
    slug = SLUG_RE.sub("-", folded).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if len(slug) > max_len:
        slug = slug[:max_len].rstrip("-")
    if not slug:
        digest = hashlib.sha1((text or "").encode("utf-8")).hexdigest()[:8]
        slug = f"entry-{digest}"
    return slug


def normalize_url(url: str | None) -> str | None:
    """Normalise a URL for storage and duplicate detection.

    Keeps the path (it often identifies the resource) but drops tracking
    parameters, fragments and default ports, and lowercases the host.
    """
    if not url:
        return None
    url = url.strip()
    if url.startswith("//"):
        url = "https:" + url
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", url):
        url = "https://" + url
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return None
    try:
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        # Malformed authority such as "host:events"; keep the host only.
        host = re.sub(r":.*$", "", parts.netloc).lower()
        port = None
    if not host:
        return None
    netloc = host
    if port and port not in (80, 443):
        netloc = f"{host}:{port}"
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=False)
             if k.lower() not in TRACKING_PARAMS]
    path = parts.path or ""
    if path == "/":
        path = ""
    elif path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit((parts.scheme, netloc, path, urlencode(query), ""))


def host_of(url: str | None) -> str | None:
    if not url:
        return None
    normalized = normalize_url(url)
    if not normalized:
        return None
    return urlsplit(normalized).hostname


def registrable_domain(host: str | None) -> str | None:
    """Best effort registrable domain, e.g. api.example.co.uk -> example.co.uk."""
    if not host:
        return None
    host = host.lower().strip(".")
    if host.startswith("www."):
        host = host[4:]
    if re.fullmatch(r"[\d.]+", host):
        return host
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    last_two = ".".join(labels[-2:])
    if last_two in MULTI_PART_SUFFIXES and len(labels) >= 4:
        return ".".join(labels[-3:])
    return last_two


def provider_identity(url: str | None, fallback_name: str | None = None) -> tuple[str, str | None]:
    """Derive (provider_id, domain) for an entry.

    Hosted project pages keep their first path segment so that
    "someone.github.io/project" does not merge with every other GitHub Pages
    project.
    """
    host = host_of(url)
    if not host:
        slug = slugify(fallback_name or "unknown-provider", 32)
        return slug, None
    base = registrable_domain(host) or host
    if base in HOSTING_DOMAINS or host in HOSTING_DOMAINS:
        if host != base:
            # The subdomain carries the project identity: user.github.io,
            # site.netlify.app, project.appspot.com.
            return host, host
        path = urlsplit(normalize_url(url) or "").path.strip("/")
        segment = path.split("/")[0] if path else ""
        segment = re.sub(r"[^a-z0-9.-]", "", segment.lower())
        provider = f"{segment}.{base}" if segment else host
        return provider.strip("."), provider
    # Sub-domains carry meaning for API hosts (api.x.com vs docs.x.com) only
    # when they are not generic service prefixes.
    generic = {"api", "www", "docs", "developer", "developers", "data", "open",
               "portal", "dashboard", "console", "app", "login", "auth",
               "wiki", "en", "blog", "help", "support", "status", "community",
               "forum", "news", "shop", "store", "download", "downloads"}
    first = host.split(".")[0]
    if base == host or first in generic or first in HOSTING_DOMAINS:
        return base, base
    return host, host


def normalize_name_for_match(name: str) -> str:
    """Loose normalisation used for duplicate detection."""
    n = _ascii_fold(name or "").lower()
    n = re.sub(r"\b(api|apis|dataset|data|open|public|free|the)\b", " ", n)
    n = SLUG_RE.sub(" ", n)
    return " ".join(n.split())


def dedupe_key(provider_domain: str | None, name: str) -> str:
    return f"{provider_domain or 'unknown'}|{slugify(normalize_name_for_match(name) or name, 48)}"


def unique_id(base: str, existing: Iterable[str]) -> str:
    taken = set(existing)
    if base not in taken:
        return base
    for i in range(2, 1000):
        candidate = f"{base}-{i}"
        if candidate not in taken:
            return candidate
    raise RuntimeError(f"cannot allocate unique id for {base}")
