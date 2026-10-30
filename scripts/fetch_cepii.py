"""Fetch CEPII GeoDist bilateral distances (Mayer & Zignago 2011).

dist_cepii.xls holds great-circle distances between 225 countries, computed
from the most populated cities (`dist`), capitals (`distcap`) and population-
weighted city pairs (`distw`).
"""

from __future__ import annotations

import zipfile

from _common import RAW, download, log

URL = "https://www.cepii.fr/distance/dist_cepii.zip"


def main() -> None:
    z = download(URL, RAW / "cepii" / "dist_cepii.zip")
    out = RAW / "cepii" / "dist_cepii.xls"
    if not out.exists():
        with zipfile.ZipFile(z) as zf:
            out.write_bytes(zf.read("dist_cepii.xls"))
    log(f"ok: {out.relative_to(RAW)}")


if __name__ == "__main__":
    main()
