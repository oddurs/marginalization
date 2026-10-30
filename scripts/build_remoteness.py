"""Compute the economic remoteness index from CEPII distances and WDI GDP.

    remoteness_i = sum_{j != i} (GDP_j / sum_{k != i} GDP_k) * dist_ij

i.e. the GDP-weighted average distance (km) from country i to the world's
output. GDP is current US$ averaged over the analysis window. `dist` is the
CEPII great-circle distance between the countries' most populous cities.

CEPII (2011 release) uses some legacy codes; they are mapped to current ISO
codes, and successor states inherit the predecessor's distances (noted in
the output's `dist_proxy` column). Taiwan has CEPII distances but no WDI GDP
and so carries no weight; this omission is noted in the paper's appendix.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from _common import PROCESSED, RAW, WINDOW, log

LEGACY = {"ROM": "ROU", "TMP": "TLS", "ZAR": "COD", "PAL": "PSE", "YUG": "SRB"}
# successor/proxy codes -> code whose CEPII distances they inherit
PROXY = {"MNE": "SRB", "SSD": "SDN", "CUW": "ANT", "SXM": "ANT"}


def load_distances() -> pd.DataFrame:
    d = pd.read_excel(RAW / "cepii" / "dist_cepii.xls")[["iso_o", "iso_d", "dist"]]
    d = d.replace({"iso_o": LEGACY, "iso_d": LEGACY})
    extra = []
    for new, old in PROXY.items():
        a = d[d.iso_o == old].assign(iso_o=new)
        b = d[d.iso_d == old].assign(iso_d=new)
        extra += [a, b]
    d = pd.concat([d, *extra], ignore_index=True)
    # proxy-to-proxy pairs (e.g. MNE-SSD) are covered via their parents
    d = d.drop_duplicates(["iso_o", "iso_d"])
    return d


def main() -> None:
    wdi = pd.read_csv(RAW / "wdi" / "wdi_long.csv")
    eco = pd.read_csv(RAW / "wdi" / "economies.csv")
    countries = set(eco.loc[~eco["aggregate"], "iso3"])
    gdp = (wdi[(wdi.indicator == "NY.GDP.MKTP.CD") & wdi.year.between(*WINDOW)
               & wdi.economy.isin(countries)]
           .groupby("economy").value.mean().rename("gdp"))
    d = load_distances()
    d = d[d.iso_o != d.iso_d].merge(gdp, left_on="iso_d", right_index=True)
    d["w"] = d.gdp / d.groupby("iso_o").gdp.transform("sum")
    r = (d.assign(wd=d.w * d.dist).groupby("iso_o")
         .agg(remoteness_km=("wd", "sum"), partners=("iso_d", "nunique"),
              gdp_share_covered=("gdp", "sum")))
    r["gdp_share_covered"] = r.gdp_share_covered / gdp.sum()
    r = r[r.index.isin(countries)].copy()
    r["dist_proxy"] = r.index.map(lambda c: PROXY.get(c, ""))
    r.index.name = "iso3"
    r["remoteness_km"] = r.remoteness_km.round(0)
    r["gdp_share_covered"] = r.gdp_share_covered.round(4)
    r.sort_index().to_csv(PROCESSED / "remoteness.csv")
    log(f"{len(r)} countries; median remoteness {np.median(r.remoteness_km):,.0f} km")


if __name__ == "__main__":
    main()
