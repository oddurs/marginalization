"""Fetch the IAB brain-drain dataset (Bruecker, Capuano & Marfouk 2013).

Emigration rates to 20 OECD destinations by country of origin and education,
population aged 25+, 1980-2010 in five-year steps.
"""

from __future__ import annotations

from _common import RAW, download, log

URL = "https://doku.iab.de/daten/brain-drain/iabbd_8010_v1_emigration.xls"


def main() -> None:
    download(URL, RAW / "iab" / "iabbd_8010_v1_emigration.xls")
    log("ok")


if __name__ == "__main__":
    main()
