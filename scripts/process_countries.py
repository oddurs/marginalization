"""Join every source into one tidy country table: data/processed/countries.csv.

One row per sovereign or territorial economy in the World Bank list. Columns
are documented in data/SOURCES.md. Cross-sectional WDI values are averages
over the analysis window (WINDOW in _common.py) unless noted.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from _common import PROCESSED, RAW, WINDOW, log
from _names import to_iso3

# The "escapees" discussed in Section 10 and the countries labelled on charts.
ESCAPEES = ["ISL", "FRO", "SGP", "MUS"]
LABELS = {
    "TON": "Tonga", "TUV": "Tuvalu", "KIR": "Kiribati", "FJI": "Fiji",
    "WSM": "Samoa", "VUT": "Vanuatu", "SLB": "Solomon Is.", "MHL": "Marshall Is.",
    "FSM": "Micronesia", "PLW": "Palau", "NRU": "Nauru",
    "MDV": "Maldives", "MUS": "Mauritius", "SYC": "Seychelles", "CPV": "Cabo Verde",
    "COM": "Comoros", "STP": "S\\~ao Tom\\'e", "JAM": "Jamaica", "HTI": "Haiti",
    "BRB": "Barbados", "GUY": "Guyana", "DMA": "Dominica", "TTO": "Trinidad",
    "ISL": "Iceland", "FRO": "Faroes", "SGP": "Singapore", "MLT": "Malta",
    "NZL": "New Zealand", "AUS": "Australia", "USA": "United States",
    "CHN": "China", "IND": "India", "DEU": "Germany", "GBR": "UK", "QAT": "Qatar",
    "LUX": "Luxembourg", "NLD": "Netherlands", "MNG": "Mongolia", "NPL": "Nepal",
    "BTN": "Bhutan", "LSO": "Lesotho", "TCD": "Chad", "CHE": "Switzerland",
    "KOR": "Korea", "CHL": "Chile", "ARG": "Argentina", "PNG": "PNG",
    "TJK": "Tajikistan", "KGZ": "Kyrgyzstan",
}
PACIFIC_SUBREGIONS = {"Melanesia", "Micronesia", "Polynesia"}


def wdi_window(wdi: pd.DataFrame, code: str, years=WINDOW) -> pd.Series:
    s = wdi[(wdi.indicator == code) & wdi.year.between(*years)]
    return s.groupby("economy").value.mean()


def wdi_latest(wdi: pd.DataFrame, code: str, years=(2013, 2023)) -> pd.DataFrame:
    s = wdi[(wdi.indicator == code) & wdi.year.between(*years)].dropna(subset=["value"])
    s = s.sort_values("year").groupby("economy").last()
    return s[["value", "year"]]


def groups() -> pd.DataFrame:
    m49 = pd.read_csv(RAW / "m49" / "m49.csv")
    g = pd.DataFrame({
        "iso3": m49["ISO-alpha3 Code"],
        "m49": m49["M49 Code"].astype(int),
        "subregion": m49["Sub-region Name"],
        "sids": m49["Small Island Developing States (SIDS)"].notna().astype(int),
        "lldc": m49["Land Locked Developing Countries (LLDC)"].notna().astype(int),
    }).dropna(subset=["iso3"])
    g["pacific"] = (g.subregion.isin(PACIFIC_SUBREGIONS) & (g.sids == 1)).astype(int)
    return g.set_index("iso3")


def lsci_annual() -> pd.DataFrame:
    """Annual mean LSCI per ISO3 (quarterly series averaged)."""
    raw = pd.read_csv(RAW / "unctad" / "US_LSCI.csv", dtype={"Economy": str})
    val = "Index (average Q1 2023 = 100)"
    raw = raw[raw.Economy.str.fullmatch(r"\d{3}")]
    m49 = groups().reset_index()[["iso3", "m49"]]
    raw["m49"] = raw.Economy.astype(int)
    raw = raw.merge(m49, on="m49", how="inner")
    raw["year"] = raw.Quarter.str[:4].astype(int)
    full = raw.groupby("year").Quarter.nunique()
    raw = raw[raw.year.isin(full[full == 4].index)]
    return raw.groupby(["iso3", "year"])[val].mean().rename("lsci").reset_index()


def cables() -> pd.DataFrame:
    """International submarine cables in service, per landing country."""
    data = json.loads((RAW / "cables" / "cables.json").read_text())
    rows = []
    for c in data:
        if c.get("is_planned") or not c.get("rfs_year") or c["rfs_year"] > 2025:
            continue
        isos = {to_iso3(lp["country"]) for lp in c.get("landing_points", [])
                if lp.get("country")}
        if len(isos) < 2:  # domestic cable
            continue
        for iso in isos:
            rows.append({"iso3": iso, "cable": c["id"], "rfs": c["rfs_year"]})
    df = pd.DataFrame(rows)
    return df.groupby("iso3").agg(cables_intl=("cable", "nunique"),
                                  first_cable_year=("rfs", "min"))


def diabetes() -> pd.DataFrame:
    d = pd.read_csv(RAW / "ncdrisc" /
                    "NCD_RisC_Lancet_2024_Diabetes_age_standardised_countries.csv")
    col = "Prevalence of diabetes (18+ years)"
    # Simple mean of the male and female age-standardised estimates.
    d = d.groupby(["ISO", "Year"])[col].mean().mul(100).rename("diabetes").reset_index()
    return d.rename(columns={"ISO": "iso3", "Year": "year"})


def emigration() -> pd.DataFrame:
    x = pd.read_excel(RAW / "iab" / "iabbd_8010_v1_emigration.xls",
                      sheet_name="RATE MEN and WOMEN", header=None)
    years = x.iloc[0].ffill()
    edu = x.iloc[1]
    body = x.iloc[3:].copy()
    body = body[body[0].notna() & (body[0] != "World")]
    out = pd.DataFrame({"iso3": [to_iso3(n) for n in body[0]]})
    for y in (2000, 2010):
        for level, name in (("High", "high"), ("Total", "total")):
            idx = [i for i in x.columns if years[i] == y and edu[i] == level][0]
            out[f"emig_{name}_{y}"] = (body[idx].astype(float) * 100).values
    return out.groupby("iso3").first()


def main() -> None:
    wdi = pd.read_csv(RAW / "wdi" / "wdi_long.csv")
    eco = pd.read_csv(RAW / "wdi" / "economies.csv")
    eco = eco[~eco["aggregate"]].set_index("iso3")

    df = eco[["name", "region", "income"]].copy()
    df = df.join(groups()[["subregion", "sids", "lldc", "pacific"]], how="left")
    for c in ("sids", "lldc", "pacific"):
        df[c] = df[c].fillna(0).astype(int)
    df["escape"] = df.index.isin(ESCAPEES).astype(int)
    df["label"] = df.index.map(lambda i: LABELS.get(i, ""))

    df["pop"] = wdi_window(wdi, "SP.POP.TOTL")
    df["gdppc_ppp"] = wdi_window(wdi, "NY.GDP.PCAP.PP.KD")
    df["gdppc_usd"] = wdi_window(wdi, "NY.GDP.PCAP.CD")
    df["remittances_gdp"] = wdi_window(wdi, "BX.TRF.PWKR.DT.GD.ZS")
    df["internet"] = wdi_window(wdi, "IT.NET.USER.ZS")
    df["broadband"] = wdi_window(wdi, "IT.NET.BBND.P2")
    df["co2pc"] = wdi_window(wdi, "EN.GHG.CO2.PC.CE.AR5")
    df["trade_gdp"] = wdi_window(wdi, "NE.TRD.GNFS.ZS")
    df["gov_eff"] = wdi_window(wdi, "GOV_WGI_GE.EST")
    df["tourism_exports"] = wdi_window(wdi, "ST.INT.RCPT.XP.ZS", years=(2015, 2019))
    doc = wdi_latest(wdi, "SH.MED.PHYS.ZS")
    df["doctors"] = doc.value
    df["doctors_year"] = doc.year

    rem = pd.read_csv(PROCESSED / "remoteness.csv", index_col="iso3")
    df = df.join(rem[["remoteness_km"]])

    ls = lsci_annual()
    last = ls.year.max()
    df["lsci"] = ls[ls.year == last].set_index("iso3").lsci
    df["lsci_year"] = last
    df["lsci_2006"] = ls[ls.year == 2006].set_index("iso3").lsci

    df = df.join(cables())
    # Coastal economies with no international cable get 0; landlocked stay blank.
    coastal = df.lsci.notna() | df.sids.eq(1)
    df.loc[coastal & df.cables_intl.isna(), "cables_intl"] = 0

    dia = diabetes()
    df["diabetes_2022"] = dia[dia.year == 2022].set_index("iso3").diabetes
    df["diabetes_1990"] = dia[dia.year == 1990].set_index("iso3").diabetes
    df = df.join(emigration())

    # Climate exposure: low-elevation population (2015, the latest WDI year)
    # and disaster displacement per 1,000 residents, averaged 2008-2023.
    df["low_elev"] = wdi_latest(wdi, "EN.POP.EL5M.ZS", years=(2015, 2015)).value
    disp = wdi[(wdi.indicator == "VC.IDP.NWDS") & wdi.year.between(2008, 2023)]
    pop = wdi[(wdi.indicator == "SP.POP.TOTL") & wdi.year.between(2008, 2023)]
    disp = disp.merge(pop, on=["economy", "year"], suffixes=("", "_pop"))
    disp["rate"] = disp.value / disp.value_pop * 1000
    # Years without a reported displacement count as zero within 2008-2023.
    df["displaced_per_k"] = disp.groupby("economy").rate.sum() / 16

    # Log transforms used by the charts and the regression.
    df["log_pop"] = np.log10(df["pop"])
    df["log_remote"] = np.log10(df.remoteness_km)
    df["log_gdppc"] = np.log10(df.gdppc_ppp)
    df["remote_kkm"] = df.remoteness_km / 1000
    df["pop_m"] = df["pop"] / 1e6

    df.index.name = "iso3"
    df = df.round(4).sort_index()
    df.to_csv(PROCESSED / "countries.csv")
    log(f"{len(df)} economies, {df.sids.sum()} SIDS, {df.lldc.sum()} LLDC; "
        f"LSCI year {last}")


if __name__ == "__main__":
    main()
