"""Answer the catalog's reference questions and record the real output.

Usage: python scripts/answer_checks.py [--out reports/answer-checks.md]
"""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

QUESTIONS = [
    ("Historical weather observations for Europe",
     ["search", "historical", "--category", "weather-climate", "--limit", "8"]),
    ("Free geospatial sources that allow commercial use",
     ["search", "--category", "geospatial", "--commercial", "allowed", "--limit", "8"]),
    ("Medical datasets downloadable without authentication",
     ["search", "--category", "health-medical", "--kind", "dataset", "--access", "public",
      "--limit", "8"]),
    ("Freemium providers with a documented free tier",
     ["search", "--pricing", "freemium", "--free-tier", "--limit", "8"]),
    ("Alternatives to a paid or freemium provider",
     ["alternatives", "openweathermap.org/openweathermap", "--pricing", "free,freemium",
      "--limit", "6"]),
    ("Realtime sources",
     ["search", "--update-frequency", "realtime", "--limit", "8"]),
    ("Static or periodic archive sources",
     ["search", "--update-frequency", "static,periodic", "--limit", "8"]),
    ("Verified entries only",
     ["search", "--confidence", "verified", "--limit", "8"]),
]


def run(args: list[str]) -> str:
    proc = subprocess.run([PY, "-m", "regipy.cli", *args], cwd=ROOT,
                          capture_output=True, text=True, timeout=180)
    out = (proc.stdout or "").strip()
    if proc.returncode not in (0, 1):
        out += f"\n(exit {proc.returncode}) {proc.stderr.strip()[:400]}"
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=ROOT / "reports" / "answer-checks.md")
    args = parser.parse_args()

    lines = ["# Reference question checks", "",
             f"Generated {dt.date.today().isoformat()} by `python scripts/answer_checks.py`.",
             "", "Each block is the literal output of the command shown above it.", ""]
    for title, cmd in QUESTIONS:
        lines.append(f"## {title}")
        lines.append("")
        lines.append("```bash")
        lines.append("python -m regipy.cli " + " ".join(cmd))
        lines.append("```")
        lines.append("")
        output = run(cmd)
        lines.append("```text")
        lines.extend(output.splitlines()[:18])
        lines.append("```")
        lines.append("")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
