"""Shared helpers for the data pipeline: paths, cached downloads, manifest.

Every fetcher downloads into data/raw/<source>/ exactly once. A download is
skipped when the target file already exists, so re-running the pipeline is
idempotent and offline-friendly. Each file's URL, SHA-256 and first access
date are recorded in data/raw/MANIFEST.json, which is committed so the
provenance of every number survives even when raw files are git-ignored.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
GENERATED = ROOT / "generated"
FIGURES = ROOT / "figures"
MANIFEST = RAW / "MANIFEST.json"

for _d in (RAW, PROCESSED, GENERATED, FIGURES):
    _d.mkdir(parents=True, exist_ok=True)

# Analysis window used throughout: averages over these years smooth out
# single-year noise (and the 2020 pandemic dip) in the cross-sections.
WINDOW = (2019, 2023)


def log(msg: str) -> None:
    print(f"[{Path(sys.argv[0]).stem}] {msg}", flush=True)


def _load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def record(path: Path, url: str, note: str = "") -> None:
    """Record a raw file in the manifest (keeps the first access date)."""
    manifest = _load_manifest()
    key = str(path.relative_to(RAW))
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    entry = manifest.get(key, {})
    if entry.get("sha256") != sha:
        entry = {
            "url": url,
            "sha256": sha,
            "bytes": path.stat().st_size,
            "accessed": dt.date.today().isoformat(),
        }
        if note:
            entry["note"] = note
    manifest[key] = entry
    MANIFEST.write_text(json.dumps(dict(sorted(manifest.items())), indent=2) + "\n")


def download(url: str, dest: Path, *, retries: int = 4, timeout: int = 300) -> Path:
    """Download url to dest with curl unless it is already cached.

    curl is used rather than `requests` because some statistical portals
    (UNCTADstat, NCD-RisC) reject or misroute python-requests connections.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        return dest
    tmp = dest.with_suffix(dest.suffix + ".part")
    cmd = ["curl", "--fail", "--silent", "--show-error", "--location",
           "--retry", str(retries), "--retry-delay", "2", "--retry-all-errors",
           "--max-time", str(timeout), "--output", str(tmp), url]
    subprocess.run(cmd, check=True)
    os.replace(tmp, dest)
    record(dest, url)
    log(f"downloaded {dest.relative_to(ROOT)} ({dest.stat().st_size:,} bytes)")
    return dest
