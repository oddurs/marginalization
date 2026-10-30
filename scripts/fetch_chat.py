"""Fetch the CHAT dataset (Comin & Hobijn 2009, NBER WP 15319).

Cross-country Historical Adoption of Technology: 100+ technologies,
150+ countries, 1800-2008.
"""

from __future__ import annotations

from _common import RAW, download, log

URL = "https://data.nber.org/data-appendix/w15319/FinalCHAT_72909.csv"


def main() -> None:
    download(URL, RAW / "chat" / "FinalCHAT_72909.csv")
    log("ok")


if __name__ == "__main__":
    main()
