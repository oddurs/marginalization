"""Group time series for the line charts.

Outputs (data/processed/):
  lsci_groups.csv       annual LSCI medians: SIDS, hubs, all countries
  diabetes_groups.csv   NCD-RisC diabetes medians: Pacific SIDS, all SIDS, all countries
  internet_groups.csv   internet use medians: SIDS, LLDC, high income; gaps
  remittances_top.csv   the 20 most remittance-dependent economies

Group statistics are unweighted medians across countries, so that one large
member (e.g. Papua New Guinea among Pacific states) cannot dominate a line.
"""

from __future__ import annotations

import pandas as pd

from _common import PROCESSED, RAW, WINDOW, log
from process_countries import diabetes, lsci_annual

HUB_COUNT = 10


def main() -> None:
    c = pd.read_csv(PROCESSED / "countries.csv", index_col="iso3")
    sids = set(c.index[c.sids == 1])
    pacific = set(c.index[c.pacific == 1])
    lldc = set(c.index[c.lldc == 1])
    hic = set(c.index[c.income == "HIC"])

    # -------------------------------------------------------------- LSCI
    ls = lsci_annual()
    ls = ls[ls.iso3.isin(c.index)]
    # Hubs are fixed at the start of the series (top 10 in 2006) so that the
    # group is not selected on its later success.
    hubs = set(ls[ls.year == 2006].nlargest(HUB_COUNT, "lsci").iso3)
    rows = []
    for y, g in ls.groupby("year"):
        rows.append({
            "year": y,
            "sids": g[g.iso3.isin(sids)].lsci.median(),
            "sids_p25": g[g.iso3.isin(sids)].lsci.quantile(0.25),
            "sids_p75": g[g.iso3.isin(sids)].lsci.quantile(0.75),
            "pacific": g[g.iso3.isin(pacific)].lsci.median(),
            "hubs": g[g.iso3.isin(hubs)].lsci.median(),
            "all": g.lsci.median(),
            "n_sids": g.iso3.isin(sids).sum(),
        })
    lsci = pd.DataFrame(rows)
    lsci["hub_sids_gap"] = lsci.hubs - lsci.sids
    lsci["hub_sids_ratio"] = lsci.hubs / lsci.sids
    lsci.round(3).to_csv(PROCESSED / "lsci_groups.csv", index=False)
    pd.Series(sorted(hubs), name="iso3").to_csv(PROCESSED / "lsci_hubs.csv", index=False)

    # Per-country change 2006 -> latest, for the trade section.
    first, last = 2006, ls.year.max()
    wide = ls[ls.year.isin([first, last])].pivot(index="iso3", columns="year", values="lsci")
    wide.columns = ["lsci_first", "lsci_last"]
    wide["change"] = wide.lsci_last - wide.lsci_first
    wide["pct_change"] = (wide.lsci_last / wide.lsci_first - 1) * 100
    wide["sids"] = wide.index.isin(sids).astype(int)
    wide["hub"] = wide.index.isin(hubs).astype(int)
    wide.round(3).to_csv(PROCESSED / "lsci_change.csv")

    # -------------------------------------------------------------- diabetes
    d = diabetes()
    rows = []
    for y, g in d.groupby("year"):
        rows.append({
            "year": y,
            "pacific": g[g.iso3.isin(pacific)].diabetes.median(),
            "sids": g[g.iso3.isin(sids)].diabetes.median(),
            "all": g.diabetes.median(),
            "pacific_max": g[g.iso3.isin(pacific)].diabetes.max(),
            "pacific_min": g[g.iso3.isin(pacific)].diabetes.min(),
        })
    pd.DataFrame(rows).round(3).to_csv(PROCESSED / "diabetes_groups.csv", index=False)

    # -------------------------------------------------------------- internet
    wdi = pd.read_csv(RAW / "wdi" / "wdi_long.csv")
    # Access (internet users) versus intensity (fixed broadband lines).
    frames = []
    for code, tag in (("IT.NET.USER.ZS", "net"), ("IT.NET.BBND.P2", "bb")):
        s = wdi[(wdi.indicator == code) & wdi.economy.isin(c.index)
                & wdi.year.between(1995, WINDOW[1])]
        g = s.groupby("year")
        frames.append(pd.DataFrame({
            f"{tag}_sids": g.apply(lambda x: x[x.economy.isin(sids)].value.median()),
            f"{tag}_pacific": g.apply(lambda x: x[x.economy.isin(pacific)].value.median()),
            f"{tag}_lldc": g.apply(lambda x: x[x.economy.isin(lldc)].value.median()),
            f"{tag}_hic": g.apply(lambda x: x[x.economy.isin(hic)].value.median()),
        }))
    it = pd.concat(frames, axis=1).reset_index()
    for tag in ("net", "bb"):
        it[f"{tag}_gap"] = it[f"{tag}_hic"] - it[f"{tag}_sids"]    # absolute gap
        it[f"{tag}_ratio"] = it[f"{tag}_hic"] / it[f"{tag}_sids"]  # relative gap
    it.round(3).to_csv(PROCESSED / "internet_groups.csv", index=False)

    # -------------------------------------------------------------- remittances
    r = c.dropna(subset=["remittances_gdp"]).nlargest(20, "remittances_gdp")
    r = r[["name", "remittances_gdp", "sids", "lldc", "pacific"]].copy()
    r["short"] = r.name.str.replace(r",.*$", "", regex=True).str.replace(
        "Kyrgyz Republic", "Kyrgyzstan")
    r["group"] = r.apply(lambda x: "sids" if x.sids else ("lldc" if x.lldc else "other"), axis=1)
    r = r.iloc[::-1]  # ascending for a horizontal bar chart drawn bottom-up
    r["pos"] = range(len(r))
    r["other"] = ((r.sids == 0) & (r.lldc == 0)).astype(int)
    assert not r.short.str.contains(",").any()
    r[["pos", "short", "remittances_gdp", "sids", "lldc", "pacific", "other"]].round(2).to_csv(
        PROCESSED / "remittances_top.csv", index_label="iso3")

    log(f"LSCI {first}-{last}, hubs={sorted(hubs)}")


if __name__ == "__main__":
    main()
