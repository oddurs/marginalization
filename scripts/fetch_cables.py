"""Fetch TeleGeography's public submarine cable data (submarinecablemap.com).

The site's front end reads a small JSON API: one index of all cables and one
JSON document per cable listing its landing points (with country), its
ready-for-service (RFS) year and whether it is still planned. All per-cable
documents are bundled into data/raw/cables/cables.json.
"""

from __future__ import annotations

import json
import time

import requests

from _common import RAW, download, log, record

BASE = "https://www.submarinecablemap.com/api/v3"


def main() -> None:
    index = download(f"{BASE}/cable/all.json", RAW / "cables" / "all.json")
    out = RAW / "cables" / "cables.json"
    if out.exists():
        log("cached")
        return
    ids = [c["id"] for c in json.loads(index.read_text())]
    session = requests.Session()
    cables = []
    for i, cid in enumerate(ids):
        for attempt in range(5):
            try:
                r = session.get(f"{BASE}/cable/{cid}.json", timeout=60)
                r.raise_for_status()
                cables.append(r.json())
                break
            except requests.RequestException:
                time.sleep(2 ** attempt)
        else:
            raise RuntimeError(f"failed to fetch cable {cid}")
        if i % 100 == 0:
            log(f"{i}/{len(ids)}")
    out.write_text(json.dumps(cables, indent=0, sort_keys=True))
    record(out, f"{BASE}/cable/<id>.json",
           note=f"{len(cables)} cable documents bundled")
    log(f"wrote {len(cables)} cables")


if __name__ == "__main__":
    main()
