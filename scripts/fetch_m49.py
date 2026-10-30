"""Fetch the UN M49 standard country table (regions, ISO codes, SIDS, LLDC).

The UN Statistics Division's M49 overview page is the authoritative source for
both country groupings used in this paper: Small Island Developing States
(SIDS) and Landlocked Developing Countries (LLDCs).
"""

from __future__ import annotations

from io import StringIO

import pandas as pd

from _common import RAW, download, log

URL = "https://unstats.un.org/unsd/methodology/m49/overview/"


def main() -> None:
    html = download(URL, RAW / "m49" / "m49_overview.html")
    out = RAW / "m49" / "m49.csv"
    tables = pd.read_html(StringIO(html.read_text(encoding="utf-8")))
    m49 = tables[0]  # first table is the English version
    m49.to_csv(out, index=False)
    log(f"{len(m49)} areas; SIDS={m49.iloc[:, -1].notna().sum()}, "
        f"LLDC={m49.iloc[:, -2].notna().sum()}")


if __name__ == "__main__":
    main()
