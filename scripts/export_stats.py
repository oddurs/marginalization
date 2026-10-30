"""Compute every number quoted in the prose and write LaTeX macros.

Outputs:
  generated/stats.tex         \\newcommand definitions, one per statistic
  generated/regression.tex    the remoteness-vs-scale regression table
  generated/escape_table.tex  the "Who Escapes?" comparison table
  data/processed/regression.csv, escape.csv  (same numbers, machine-readable)

Rounding is centralised in `fmt` so the same quantity is always printed the
same way. Macro names are letters only (a LaTeX requirement).
"""

from __future__ import annotations

import json
import re

import numpy as np
import pandas as pd

from _common import GENERATED, PROCESSED, RAW, ROOT, WINDOW, log

MACROS: dict[str, str] = {}


def fmt(x: float, nd: int = 0) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        raise ValueError("refusing to export a missing value")
    s = f"{x:,.{nd}f}"
    return s.replace(",", "{,}")


def m(name: str, value, nd: int = 0) -> None:
    assert re.fullmatch(r"[A-Za-z]+", name), name
    assert name not in MACROS, f"duplicate macro {name}"
    MACROS[name] = value if isinstance(value, str) else fmt(float(value), nd)


def my(name: str, year) -> None:
    """A calendar year: printed as a plain integer, no thousands separator."""
    m(name, str(int(year)))


def ols(y: pd.Series, X: pd.DataFrame) -> dict:
    """OLS with HC1 heteroskedasticity-robust standard errors."""
    X = X.assign(const=1.0)
    data = pd.concat([y, X], axis=1).dropna()
    yv, Xv = data.iloc[:, 0].values, data.iloc[:, 1:].values
    n, k = Xv.shape
    beta, *_ = np.linalg.lstsq(Xv, yv, rcond=None)
    resid = yv - Xv @ beta
    xtx_inv = np.linalg.inv(Xv.T @ Xv)
    meat = Xv.T @ (Xv * resid[:, None] ** 2)
    cov = xtx_inv @ meat @ xtx_inv * n / (n - k)
    se = np.sqrt(np.diag(cov))
    r2 = 1 - (resid ** 2).sum() / ((yv - yv.mean()) ** 2).sum()
    names = list(data.columns[1:])
    return {"coef": dict(zip(names, beta)), "se": dict(zip(names, se)),
            "n": n, "r2": r2}


def stars(b: float, se: float) -> str:
    t = abs(b / se)
    return "^{***}" if t > 2.576 else "^{**}" if t > 1.96 else "^{*}" if t > 1.645 else ""


def main() -> None:
    c = pd.read_csv(PROCESSED / "countries.csv", index_col="iso3")
    sids = c[c.sids == 1]
    pac = c[c.pacific == 1]
    lldc = c[c.lldc == 1]
    other = c[(c.sids == 0) & (c.lldc == 0)]

    my("windowStart", WINDOW[0]); my("windowEnd", WINDOW[1])

    # ---------------------------------------------------------- definitions
    r = c.dropna(subset=["remoteness_km"])
    m("nCountriesRemote", len(r))
    m("nSIDS", len(sids)); m("nPacific", len(pac)); m("nLLDC", len(lldc))
    m48 = pd.read_csv(RAW / "m49" / "m49.csv")
    m("nSIDSunList", m48["Small Island Developing States (SIDS)"].notna().sum())
    m("remoteMedianKm", r.remoteness_km.median())
    m("remoteSIDSMedianKm", sids.remoteness_km.median())
    m("remotePacificMedianKm", pac.remoteness_km.median())
    m("remoteLLDCMedianKm", lldc.remoteness_km.median())
    for iso, nm in [("TON", "Tonga"), ("ISL", "Iceland"), ("FRO", "Faroes"),
                    ("SGP", "Singapore"), ("MUS", "Mauritius"), ("NZL", "NewZealand"),
                    ("MNG", "Mongolia"), ("TUV", "Tuvalu")]:
        m(f"remote{nm}Km", c.loc[iso, "remoteness_km"])
    lo, hi = r.remoteness_km.idxmin(), r.remoteness_km.idxmax()
    m("remoteMinName", c.loc[lo, "name"]); m("remoteMinKm", r.remoteness_km.min())
    m("remoteMaxName", c.loc[hi, "name"]); m("remoteMaxKm", r.remoteness_km.max())
    rank = r.remoteness_km.rank(ascending=False)
    m("remoteTongaRank", rank["TON"]); m("remoteIcelandRank", rank["ISL"])
    m("corrRemotePop", r[["log_remote", "log_pop"]].corr().iloc[0, 1], 2)
    m("popSIDSMedianK", sids["pop"].median() / 1e3)
    m("popPacificMedianK", pac["pop"].median() / 1e3)
    m("popTongaK", c.loc["TON", "pop"] / 1e3)
    m("shareSIDSUnderOneM", (sids["pop"] < 1e6).mean() * 100)

    # ---------------------------------------------------------- regression
    y = c.log_gdppc
    specs = {
        "(1)": ["log_remote", "log_pop"],
        "(2)": ["log_remote", "log_pop", "gov_eff"],
        "(3)": ["log_remote", "log_pop", "gov_eff", "sids", "lldc"],
    }
    res = {k: ols(y, c[v]) for k, v in specs.items()}
    labels = {"log_remote": "log remoteness", "log_pop": "log population",
              "gov_eff": "Government effectiveness", "sids": "SIDS",
              "lldc": "Landlocked (LLDC)", "const": "Constant"}
    rows = []
    for var, lab in labels.items():
        cells, ses = [], []
        for k in specs:
            if var in res[k]["coef"]:
                b, se = res[k]["coef"][var], res[k]["se"][var]
                cells.append(f"${b:.2f}{stars(b, se)}$")
                ses.append(f"$({se:.2f})$")
            else:
                cells.append(""); ses.append("")
        rows.append(f"{lab} & " + " & ".join(cells) + r" \\")
        rows.append(" & " + " & ".join(ses) + r" \\[2pt]")
    rows.append(r"\midrule")
    rows.append("Countries & " + " & ".join(str(res[k]["n"]) for k in specs) + r" \\")
    rows.append("$R^2$ & " + " & ".join(f"{res[k]['r2']:.2f}" for k in specs) + r" \\")
    (GENERATED / "regression.tex").write_text(
        "% generated by scripts/export_stats.py\n"
        r"\begin{tabular}{@{}lccc@{}}" "\n" r"\toprule" "\n"
        r" & (1) & (2) & (3) \\" "\n" r"\midrule" "\n"
        + "\n".join(rows) + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")
    pd.DataFrame([{"spec": k, "var": v, "coef": res[k]["coef"][v], "se": res[k]["se"][v],
                   "n": res[k]["n"], "r2": res[k]["r2"]}
                  for k in specs for v in res[k]["coef"]]).round(4).to_csv(
        PROCESSED / "regression.csv", index=False)
    for k, tag in zip(specs, ("One", "Two", "Three")):
        m(f"regRemote{tag}", res[k]["coef"]["log_remote"], 2)
        m(f"regRemoteSE{tag}", res[k]["se"]["log_remote"], 2)
        m(f"regPop{tag}", res[k]["coef"]["log_pop"], 2)
        m(f"regN{tag}", res[k]["n"])
        m(f"regRsq{tag}", res[k]["r2"], 2)
    m("regGov", res["(3)"]["coef"]["gov_eff"], 2)
    m("regLLDCpct", abs((10 ** res["(3)"]["coef"]["lldc"] - 1) * 100))
    m("regGovPct", (10 ** res["(3)"]["coef"]["gov_eff"] - 1) * 100)
    m("regSIDS", res["(3)"]["coef"]["sids"], 2)
    m("regSIDSse", res["(3)"]["se"]["sids"], 2)
    # Implied effect of doubling remoteness (log10 elasticity -> percent).
    m("regDoubleRemotePct", (2 ** res["(2)"]["coef"]["log_remote"] - 1) * 100)
    m("regDoubleRemotePctAbs", abs((2 ** res["(2)"]["coef"]["log_remote"] - 1) * 100))

    # ---------------------------------------------------------- trade
    lg = pd.read_csv(PROCESSED / "lsci_groups.csv").set_index("year")
    f, l = lg.index.min(), lg.index.max()
    my("lsciFirstYear", f); my("lsciLastYear", l)
    m("sidsMedianLSCI", lg.loc[l, "sids"], 1)
    m("sidsMedianLSCIfirst", lg.loc[f, "sids"], 1)
    m("pacificMedianLSCI", lg.loc[l, "pacific"], 1)
    m("hubMedianLSCI", lg.loc[l, "hubs"], 0)
    m("hubMedianLSCIfirst", lg.loc[f, "hubs"], 0)
    m("allMedianLSCI", lg.loc[l, "all"], 1)
    m("allMedianLSCIfirst", lg.loc[f, "all"], 1)
    m("hubSidsRatio", lg.loc[l, "hub_sids_ratio"], 0)
    m("hubSidsRatioFirst", lg.loc[f, "hub_sids_ratio"], 0)
    m("allSidsRatio", lg.loc[l, "all"] / lg.loc[l, "sids"], 1)
    m("allSidsRatioFirst", lg.loc[f, "all"] / lg.loc[f, "sids"], 1)
    m("allLSCIGrowthPct", (lg.loc[l, "all"] / lg.loc[f, "all"] - 1) * 100)
    m("sidsLSCIGrowthPct", (lg.loc[l, "sids"] / lg.loc[f, "sids"] - 1) * 100)
    ch = pd.read_csv(PROCESSED / "lsci_change.csv", index_col="iso3").dropna()
    cs = ch[ch.sids == 1]
    m("nSIDSlsci", len(cs)); m("nSIDSlsciFell", (cs.change < 0).sum())
    m("nAlllsci", len(ch)); m("nAlllsciFell", (ch.change < 0).sum())
    m("lsciTonga", c.loc["TON", "lsci"], 1)
    m("lsciSingapore", c.loc["SGP", "lsci"], 0)
    m("lsciTuvalu", c.loc["TUV", "lsci"], 1)
    m("lsciMauritius", c.loc["MUS", "lsci"], 1)
    m("lsciMauritiusFirst", c.loc["MUS", "lsci_2006"], 1)
    hubs = pd.read_csv(PROCESSED / "lsci_hubs.csv").iso3
    short = {"HKG": "Hong Kong", "BEL": "Belgium", "JPN": "Japan"}
    m("hubList", ", ".join(short.get(h) or c.loc[h, "label"] for h in sorted(hubs)))

    # ---------------------------------------------------------- technology
    cab = c.dropna(subset=["cables_intl"])
    m("cablesSIDSMedian", cab[cab.sids == 1].cables_intl.median())
    m("cablesOtherMedian", cab[cab.sids == 0].cables_intl.median())
    m("nSIDSOneCable", (cab[cab.sids == 1].cables_intl <= 1).sum())
    m("nSIDScables", (cab.sids == 1).sum())
    m("nPacificOneCable", (cab[cab.pacific == 1].cables_intl <= 1).sum())
    m("cablesTonga", c.loc["TON", "cables_intl"])
    m("cablesSingapore", c.loc["SGP", "cables_intl"])
    m("cablesIceland", c.loc["ISL", "cables_intl"])
    sub = cab.dropna(subset=["log_remote"])
    m("corrCablesRemote", np.corrcoef(sub.log_remote, np.log1p(sub.cables_intl))[0, 1], 2)
    m("corrCablesPop", np.corrcoef(sub.log_pop, np.log1p(sub.cables_intl))[0, 1], 2)
    cables = json.loads((RAW / "cables" / "cables.json").read_text())
    tonga_intl = [x for x in cables if x["id"] == "tonga-cable"][0]
    m("tongaCableKm", tonga_intl["length"].replace(" km", "").replace(",", "{,}"))
    my("tongaCableRFS", tonga_intl["rfs_year"])

    it = pd.read_csv(PROCESSED / "internet_groups.csv").set_index("year")
    m("netRatioFirst", it.loc[2000, "net_ratio"], 1)
    m("netRatioLast", it.loc[WINDOW[1], "net_ratio"], 2)
    m("netSidsLast", it.loc[WINDOW[1], "net_sids"], 0)
    m("netHicLast", it.loc[WINDOW[1], "net_hic"], 0)
    m("netGapPeak", it.net_gap.max(), 0); my("netGapPeakYear", it.net_gap.idxmax())
    m("netGapLast", it.loc[WINDOW[1], "net_gap"], 0)
    m("bbSidsLast", it.loc[WINDOW[1], "bb_sids"], 1)
    m("bbPacificLast", it.loc[WINDOW[1] - 1, "bb_pacific"], 1)
    m("bbHicLast", it.loc[WINDOW[1], "bb_hic"], 1)
    m("bbGapTen", it.loc[2010, "bb_gap"], 0)
    m("bbGapLast", it.loc[WINDOW[1], "bb_gap"], 0)
    m("bbRatioTen", it.loc[2010, "bb_ratio"], 1)
    m("bbRatioLast", it.loc[WINDOW[1], "bb_ratio"], 1)

    # ---------------------------------------------------------- health
    dg = pd.read_csv(PROCESSED / "diabetes_groups.csv").set_index("year")
    for y in (1990, 2022):
        m(f"diabPacific{'Ninety' if y == 1990 else 'Now'}", dg.loc[y, "pacific"], 1)
        m(f"diabSIDS{'Ninety' if y == 1990 else 'Now'}", dg.loc[y, "sids"], 1)
        m(f"diabAll{'Ninety' if y == 1990 else 'Now'}", dg.loc[y, "all"], 1)
    m("diabPacificRatioNinety", dg.loc[1990, "pacific"] / dg.loc[1990, "all"], 1)
    m("diabPacificRatioNow", dg.loc[2022, "pacific"] / dg.loc[2022, "all"], 1)
    top = c.dropna(subset=["diabetes_2022"]).nlargest(10, "diabetes_2022")
    m("diabTopTenPacific", int(top.pacific.sum()))
    m("diabTopName", top.iloc[0]["name"]); m("diabTopValue", top.iloc[0].diabetes_2022, 0)

    doc = c.dropna(subset=["doctors"])
    m("docSIDSMedian", doc[doc.sids == 1].doctors.median(), 1)
    m("docPacificMedian", doc[doc.pacific == 1].doctors.median(), 2)
    m("docOtherMedian", doc[doc.sids == 0].doctors.median(), 1)
    m("docHICMedian", doc[doc.income == "HIC"].doctors.median(), 1)
    d2 = doc.dropna(subset=["log_remote"])
    m("corrDocRemote", np.corrcoef(d2.log_remote, d2.doctors)[0, 1], 2)
    d3 = d2.dropna(subset=["log_gdppc"])
    partial = ols(d3.doctors, d3[["log_remote", "log_gdppc"]])
    m("docRemoteCoef", partial["coef"]["log_remote"], 1)
    m("docRemoteSE", partial["se"]["log_remote"], 1)

    # ---------------------------------------------------------- people
    em = c.dropna(subset=["emig_high_2010"])
    m("emigSIDSMedian", em[em.sids == 1].emig_high_2010.median(), 0)
    m("emigPacificMedian", em[em.pacific == 1].emig_high_2010.median(), 0)
    m("emigAllMedian", em.emig_high_2010.median(), 0)
    m("emigLargeMedian", em[em["pop"] >= 20e6].emig_high_2010.median(), 0)
    m("emigSmallMedian", em[em["pop"] < 1e6].emig_high_2010.median(), 0)
    m("emigTonga", c.loc["TON", "emig_high_2010"], 0)
    m("emigMauritius", c.loc["MUS", "emig_high_2010"], 0)
    m("emigIceland", c.loc["ISL", "emig_high_2010"], 0)
    m("emigSingapore", c.loc["SGP", "emig_high_2010"], 0)
    over = em[em.emig_high_2010 > 50]
    m("nEmigOverHalf", len(over)); m("nEmigOverHalfSIDS", int(over.sids.sum()))
    m("corrEmigPop", em[["emig_high_2010", "log_pop"]].corr().iloc[0, 1], 2)
    m("emigTotalSIDSMedian", em[em.sids == 1].emig_total_2010.median(), 0)
    sel = em[em.sids == 1].dropna(subset=["emig_total_2010"])
    m("emigSelectivity", (sel.emig_high_2010 / sel.emig_total_2010).median(), 1)
    rt = pd.read_csv(PROCESSED / "remittances_top.csv")
    m("remitTopName", rt.iloc[-1]["short"]); m("remitTopValue", rt.iloc[-1].remittances_gdp, 0)
    m("nRemitTopSIDS", int(rt.sids.sum())); m("nRemitTopLLDC", int(rt.lldc.sum()))
    m("remitTopN", len(rt))
    m("remitSamoa", c.loc["WSM", "remittances_gdp"], 0)
    m("remitSIDSMedian", c[c.sids == 1].remittances_gdp.median(), 1)
    m("remitWorldMedian", c.remittances_gdp.median(), 1)

    # ---------------------------------------------------------- climate
    cl = c.dropna(subset=["co2pc", "pop"])
    world_co2 = (cl.co2pc * cl["pop"]).sum()
    m("sidsCOshare", (cl[cl.sids == 1].co2pc * cl[cl.sids == 1]["pop"]).sum() / world_co2 * 100, 1)
    m("sidsPopShare", cl[cl.sids == 1]["pop"].sum() / cl["pop"].sum() * 100, 1)
    m("pacificCOshare", (cl[cl.pacific == 1].co2pc * cl[cl.pacific == 1]["pop"]).sum()
      / world_co2 * 100, 2)
    m("coSIDSMedian", cl[cl.sids == 1].co2pc.median(), 1)
    m("coHICMedian", cl[cl.income == "HIC"].co2pc.median(), 1)
    m("coPacificMedian", cl[cl.pacific == 1].co2pc.median(), 1)
    dp = c.dropna(subset=["displaced_per_k"])
    m("dispSIDSMedian", dp[dp.sids == 1].displaced_per_k.median(), 1)
    m("dispOtherMedian", dp[dp.sids == 0].displaced_per_k.median(), 1)
    m("dispSIDSRatio", dp[dp.sids == 1].displaced_per_k.median()
      / dp[dp.sids == 0].displaced_per_k.median(), 0)
    tdp = dp.nlargest(10, "displaced_per_k")
    m("nDispTopTenSIDS", int(tdp.sids.sum()))
    m("dispTopName", tdp.iloc[0]["name"]); m("dispTopValue", tdp.iloc[0].displaced_per_k, 0)
    m("lowElevTuvalu", c.loc["TUV", "low_elev"], 0)
    m("lowElevMarshall", c.loc["MHL", "low_elev"], 0)
    m("lowElevMaldives", c.loc["MDV", "low_elev"], 0)
    m("lowElevNetherlands", c.loc["NLD", "low_elev"], 0)

    # ---------------------------------------------------------- acceleration
    ad = pd.read_csv(PROCESSED / "adoption.csv").set_index("tech")
    m("lagRail", ad.loc["railpkm", "lag"], 0)
    m("lagTelephone", ad.loc["telephone", "lag"], 0)
    m("lagCars", ad.loc["vehicle_car", "lag"], 0)
    m("lagTV", ad.loc["tv", "lag"], 0)
    m("lagCell", ad.loc["cellphone", "lag"], 0)
    m("lagComputer", ad.loc["computer", "lag"], 0)
    m("gapRail", ad.loc["railpkm", "gap_ratio"], 0)
    m("gapTelephone", ad.loc["telephone", "gap_ratio"], 0)
    m("gapTV", ad.loc["tv", "gap_ratio"], 0)
    m("gapCell", ad.loc["cellphone", "gap_ratio"], 0)
    m("gapComputer", ad.loc["computer", "gap_ratio"], 0)
    m("nTechs", len(ad))
    old, new = ad[ad.frontier < 1950], ad[ad.frontier >= 1950]
    m("lagOldMedian", old.lag.median(), 0); m("lagNewMedian", new.lag.median(), 0)
    m("gapOldMedian", old.gap_ratio.median(), 0); m("gapNewMedian", new.gap_ratio.median(), 0)
    m("corrLagGap", ad[["lag", "gap_log10"]].corr().iloc[0, 1], 2)

    # ---------------------------------------------------------- who escapes
    cols = [("pop", "Population (thousands)", 1e-3, 0),
            ("remoteness_km", "Remoteness (km)", 1, 0),
            ("gdppc_ppp", "GDP per capita, PPP (\\$)", 1, 0),
            ("gov_eff", "Government effectiveness", 1, 2),
            ("lsci", f"Shipping connectivity ({l})", 1, 0),
            ("cables_intl", "International cables", 1, 0),
            ("emig_high_2010", "Tertiary emigration, 2010 (\\%)", 1, 0),
            ("tourism_exports", "Tourism, \\% of exports (2015--19)", 1, 0)]
    units = [("ISL", "Iceland"), ("FRO", "Faroe Is."), ("SGP", "Singapore"),
             ("MUS", "Mauritius")]
    table = {name: [c.loc[iso, col] * k for col, _, k, _ in cols] for iso, name in units}
    table["Pacific SIDS (median)"] = [pac[col].median() * k for col, _, k, _ in cols]
    esc = pd.DataFrame(table, index=[lab for _, lab, _, _ in cols])
    esc.round(3).to_csv(PROCESSED / "escape.csv")
    lines = []
    for (col, lab, _, nd), (_, row) in zip(cols, esc.iterrows()):
        cells = ["---" if pd.isna(v) else fmt(v, nd) for v in row.values]
        lines.append(f"{lab} & " + " & ".join(cells) + r" \\")
    head = (r"\begin{tabular}{@{}l*{5}{r}@{}}" "\n" r"\toprule" "\n"
            r" & Iceland & Faroe Is. & Singapore & Mauritius & \makecell[r]{Pacific\\SIDS} \\"
            "\n" r"\midrule" "\n")
    (GENERATED / "escape_table.tex").write_text(
        "% generated by scripts/export_stats.py\n" + head + "\n".join(lines)
        + "\n" r"\bottomrule" "\n" r"\end{tabular}" "\n")
    for iso, nm in [("ISL", "Iceland"), ("FRO", "Faroes"), ("SGP", "Singapore"),
                    ("MUS", "Mauritius")]:
        m(f"gdp{nm}", c.loc[iso, "gdppc_ppp"] / 1e3, 0)
        m(f"pop{nm}K", c.loc[iso, "pop"] / 1e3, 0)
        if not pd.isna(c.loc[iso, "gov_eff"]):
            m(f"gov{nm}", c.loc[iso, "gov_eff"], 2)
    m("gdpPacificMedian", pac.gdppc_ppp.median() / 1e3, 1)
    m("govPacificMedian", pac.gov_eff.median(), 2)
    m("gdpTonga", c.loc["TON", "gdppc_ppp"] / 1e3, 1)
    m("tourismMauritius", c.loc["MUS", "tourism_exports"], 0)

    # ---------------------------------------------------------- narrative facts
    # A handful of facts come from news reports rather than datasets; they are
    # kept, with sources, in data/manual/narrative_facts.csv.
    facts = pd.read_csv(ROOT / "data" / "manual" / "narrative_facts.csv")
    for key, val in zip(facts.key, facts.value):
        m(key, str(val))
    m("lsciSingaporeRank", c.lsci.rank(ascending=False)["SGP"])
    m("lsciTongaRank", c.lsci.rank(ascending=False)["TON"])
    m("nLsci", c.lsci.notna().sum())

    # ---------------------------------------------------------- write
    out = ["% Generated by scripts/export_stats.py -- do not edit by hand.",
           f"% {len(MACROS)} statistics."]
    out += [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(MACROS.items())]
    (GENERATED / "stats.tex").write_text("\n".join(out) + "\n")
    log(f"wrote {len(MACROS)} macros")


if __name__ == "__main__":
    main()
