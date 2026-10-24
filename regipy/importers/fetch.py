"""Download and cache upstream catalogs under .upstream/."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import urllib.request
from pathlib import Path
from typing import Any

USER_AGENT = "api-atlas-importer/1.0 (+https://github.com/CTCycle/api-atlas)"

SOURCES: dict[str, dict[str, Any]] = {
    "public-apis": {
        "repo": "public-apis/public-apis",
        "url": "https://raw.githubusercontent.com/public-apis/public-apis/master/README.md",
        "filename": "public-apis-README.md",
        "license": "MIT",
        "license_url": "https://github.com/public-apis/public-apis/blob/master/LICENSE",
        "homepage": "https://github.com/public-apis/public-apis",
    },
    "apis-guru": {
        "repo": "APIs-guru/openapi-directory",
        "url": "https://api.apis.guru/v2/list.json",
        "filename": "apisguru-list.json",
        "license": "CC0-1.0",
        "license_url": "https://github.com/APIs-guru/openapi-directory/blob/main/LICENSE",
        "homepage": "https://apis.guru",
    },
    "awesome-datasets": {
        "repo": "awesomedata/awesome-public-datasets",
        "url": "https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/master/README.rst",
        "filename": "awesome-datasets-README.rst",
        "license": "MIT",
        "license_url": "https://github.com/awesomedata/awesome-public-datasets/blob/master/LICENSE",
        "homepage": "https://github.com/awesomedata/awesome-public-datasets",
    },
}


def _download(url: str, timeout: float = 120.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def _commit_sha(repo: str, timeout: float = 20.0) -> str | None:
    try:
        data = json.loads(_download(f"https://api.github.com/repos/{repo}/commits/HEAD", timeout))
        return data.get("sha")
    except Exception:
        return None


def manifest_path(dest_dir: Path) -> Path:
    return dest_dir / "manifest.json"


def read_manifest(dest_dir: Path) -> dict[str, Any]:
    path = manifest_path(dest_dir)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def fetch_source(name: str, dest_dir: Path, force: bool = False) -> dict[str, Any]:
    """Ensure the upstream snapshot exists and return its manifest entry."""
    meta = SOURCES[name]
    dest_dir.mkdir(parents=True, exist_ok=True)
    target = dest_dir / meta["filename"]
    manifest = read_manifest(dest_dir)
    record = manifest.get(name, {})
    if target.exists() and not force and record.get("sha256"):
        return record

    body = _download(meta["url"])
    target.write_bytes(body)
    record = {
        "source": name,
        "filename": meta["filename"],
        "url": meta["url"],
        "repo": meta.get("repo"),
        "license": meta["license"],
        "license_url": meta.get("license_url"),
        "homepage": meta.get("homepage"),
        "fetched_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "commit": _commit_sha(meta["repo"]) if meta.get("repo") else None,
    }
    manifest[name] = record
    manifest_path(dest_dir).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n",
                                      encoding="utf-8")
    return record


def cached_file(name: str, dest_dir: Path) -> Path:
    return dest_dir / SOURCES[name]["filename"]
