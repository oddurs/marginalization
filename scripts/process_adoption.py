"""Adoption lags and intensity gaps by technology, from CHAT.

For each technology with usable diffusion data:

* frontier year F: the year by which the fifth country had adopted
  (adoption = first year with a positive observation). Using the fifth
  rather than the first adopter guards against stray early records.
* adoption lag: median over later adopters of (own adoption year - F).
* intensity gap: in a reference year, the ratio of median per-capita use in
  the richest quartile of countries (real GDP per capita, CHAT's own series)
  to that in the poorest half, expressed in log10 points (1 = tenfold).
  The reference year is the latest year <= 2000 in which at least 40
  countries report; for technologies in decline by then (the telegraph) the
  gap is dropped.

Technologies whose series begin for many countries in the same year (e.g. FAO
agricultural data starting in 1961) are left-censored: their "adoption" date
is the start of record keeping, so they are excluded.

This is a transparent descriptive analogue of Comin & Hobijn (2010) and Comin
& Mestieri (2018), not a replication of their structural estimates.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from _common import PROCESSED, RAW, log

# variable -> (label, era) ; curated to one series per technology
TECHS = {
    "railpkm": ("Rail (passengers)", "industrial"),
    "railtkm": ("Rail (freight)", "industrial"),
    "telephone": ("Telephone", "industrial"),
    "vehicle_car": ("Cars", "industrial"),
    "vehicle_com": ("Trucks", "industrial"),
    "elecprod": ("Electricity", "industrial"),
    "aviationpkm": ("Aviation (passengers)", "mid"),
    "aviationtkm": ("Aviation (freight)", "mid"),
    "radio": ("Radio", "mid"),
    "tv": ("Television", "mid"),
    "cabletv": ("Cable TV", "digital"),
    "cellphone": ("Mobile phones", "digital"),
    "computer": ("Computers", "digital"),
    "internetuser": ("Internet", "digital"),
}
MIN_COUNTRIES = 40
CENSOR_SHARE = 0.10


def main() -> None:
    d = pd.read_csv(RAW / "chat" / "FinalCHAT_72909.csv", low_memory=False)
    for c in [*TECHS, "xlpopulation", "xlrealgdp"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["gdppc"] = d.xlrealgdp / d.xlpopulation

    rows = []
    for var, (label, era) in TECHS.items():
        s = d.loc[d[var] > 0, ["country_name", "year", var, "xlpopulation", "gdppc"]]
        adopt = s.groupby("country_name").year.min()
        if len(adopt) < MIN_COUNTRIES:
            continue
        if (adopt == adopt.min()).mean() > CENSOR_SHARE:
            log(f"skip {var}: left-censored")
            continue
        frontier = int(adopt.nsmallest(5).max())
        later = adopt[adopt > frontier] - frontier
        lag = float(later.median())

        # intensity gap in the reference year
        counts = s[s.year <= 2000].groupby("year").country_name.nunique()
        ok = counts[counts >= MIN_COUNTRIES]
        gap, ref = np.nan, np.nan
        if len(ok):
            ref = int(ok.index.max())
            r = s[(s.year == ref)].dropna(subset=["xlpopulation", "gdppc"]).copy()
            r["pc"] = r[var] / r.xlpopulation
            q75, q50 = r.gdppc.quantile(0.75), r.gdppc.quantile(0.50)
            rich = r[r.gdppc >= q75].pc.median()
            poor = r[r.gdppc <= q50].pc.median()
            gap = float(np.log10(rich / poor))
        rows.append({"tech": var, "label": label, "era": era,
                     "frontier": frontier, "lag": lag, "adopters": len(adopt),
                     "gap_log10": gap, "gap_ratio": 10 ** gap, "ref_year": ref})

    out = pd.DataFrame(rows).sort_values("frontier")
    out.round(3).to_csv(PROCESSED / "adoption.csv", index=False)
    log(f"{len(out)} technologies")


if __name__ == "__main__":
    main()
