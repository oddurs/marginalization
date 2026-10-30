"""Fetch UNCTAD's Liner Shipping Connectivity Index (quarterly, 2006 onward).

The UNCTADstat bulk-download endpoint serves a 7-zip archive with one CSV.
Index scale: average across countries in Q1 2023 = 100.
"""

from __future__ import annotations

import py7zr

from _common import RAW, download, log

URL = "https://unctadstat-api.unctad.org/bulkdownload/US.LSCI/US_LSCI"


def main() -> None:
    arc = download(URL, RAW / "unctad" / "US_LSCI.7z")
    out = RAW / "unctad" / "US_LSCI.csv"
    if not out.exists():
        with py7zr.SevenZipFile(arc) as z:
            z.extractall(path=out.parent)
    log(f"ok: {out.relative_to(RAW)}")


if __name__ == "__main__":
    main()
