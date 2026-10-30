"""Fetch World Bank indicators (WDI and WGI) via the wbgapi package.

Output: data/raw/wdi/wdi_long.csv with columns economy, indicator, year, value.
Includes World Bank aggregates (WLD, HIC, SST, PSS, ...) for reference lines.
"""

from __future__ import annotations

import pandas as pd
import wbgapi as wb

from _common import RAW, log, record

YEARS = range(1990, 2026)

# indicator code -> (database id, short description)
INDICATORS = {
    "SP.POP.TOTL": (2, "Population, total"),
    "NY.GDP.MKTP.CD": (2, "GDP, current US$"),
    "NY.GDP.PCAP.CD": (2, "GDP per capita, current US$"),
    "NY.GDP.PCAP.PP.KD": (2, "GDP per capita, PPP, constant 2021 intl $"),
    "BX.TRF.PWKR.DT.GD.ZS": (2, "Personal remittances, received, % of GDP"),
    "SH.MED.PHYS.ZS": (2, "Physicians per 1,000 people"),
    "SH.STA.DIAB.ZS": (2, "Diabetes prevalence, % of population ages 20-79 (IDF)"),
    "IT.NET.USER.ZS": (2, "Individuals using the Internet, % of population"),
    "IT.NET.BBND.P2": (2, "Fixed broadband subscriptions per 100 people"),
    "IT.CEL.SETS.P2": (2, "Mobile cellular subscriptions per 100 people"),
    "EN.GHG.CO2.PC.CE.AR5": (2, "CO2 emissions excl. LULUCF, t CO2e per capita"),
    "ST.INT.RCPT.XP.ZS": (2, "International tourism receipts, % of total exports"),
    "NE.TRD.GNFS.ZS": (2, "Trade, % of GDP"),
    "EN.POP.EL5M.ZS": (2, "Population living below 5 m elevation, % of total"),
    "VC.IDP.NWDS": (2, "New internal displacements associated with disasters (IDMC)"),
    "GOV_WGI_GE.EST": (3, "Government Effectiveness: estimate, -2.5 to 2.5 (WGI)"),
}


def fetch_economies() -> None:
    """Economy metadata: names, region, income group, aggregate flag."""
    dest = RAW / "wdi" / "economies.csv"
    if dest.exists():
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"iso3": e["id"], "name": e["value"], "aggregate": e["aggregate"],
             "region": e["region"], "income": e["incomeLevel"],
             "lending": e["lendingType"]}
            for e in wb.economy.list(skipAggs=False)]
    pd.DataFrame(rows).sort_values("iso3").to_csv(dest, index=False)
    record(dest, "https://api.worldbank.org/v2/country (via wbgapi)")
    log(f"{len(rows)} economies")


def main() -> None:
    fetch_economies()
    dest = RAW / "wdi" / "wdi_long.csv"
    if dest.exists():
        log("cached")
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    frames = []
    for code, (db, desc) in INDICATORS.items():
        log(f"{code}: {desc}")
        # WGI (db 3) is annual only from 2002, so request that range there.
        years = YEARS if db == 2 else range(2002, 2024)
        rows = [
            {"economy": r["economy"], "indicator": code,
             "year": int(str(r["time"]).replace("YR", "")), "value": r["value"]}
            for r in wb.data.fetch(code, economy="all", time=years, db=db,
                                   skipBlanks=True)
        ]
        frames.append(pd.DataFrame(rows))
    df = pd.concat(frames, ignore_index=True)
    df = df.sort_values(["indicator", "economy", "year"])
    df.to_csv(dest, index=False)
    record(dest, "https://api.worldbank.org/v2/ (via wbgapi)",
           note="indicators: " + ", ".join(INDICATORS))
    log(f"wrote {len(df):,} rows")


if __name__ == "__main__":
    main()
