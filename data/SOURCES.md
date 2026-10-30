# Data sources

Every number in the paper is computed by a script in `scripts/` from one of the
sources below. Raw downloads are cached in `data/raw/` (git-ignored) and each
file's URL, SHA-256 checksum, size and first access date is recorded in
[`data/raw/MANIFEST.json`](raw/MANIFEST.json), which **is** committed. Processed
tables in `data/processed/` and the macros in `generated/stats.tex` are
committed too, so `make pdf` reproduces the paper exactly without network
access.

All sources were accessed on **2026-10-30**.

| # | Dataset | Used for | Fetcher | URL | Licence / terms |
|---|---------|----------|---------|-----|-----------------|
| 1 | **World Bank World Development Indicators** (and Worldwide Governance Indicators, db 3), via `wbgapi` | population, GDP, GDP per capita (PPP), remittances, physicians, internet use, fixed broadband, CO₂ per capita, tourism receipts, low-elevation population, disaster displacement (IDMC), government effectiveness | `fetch_wdi.py` | https://api.worldbank.org/v2/ | CC BY 4.0 |
| 2 | **UN M49 standard country codes** | ISO/M49 codes, sub-regions, SIDS and LLDC flags | `fetch_m49.py` | https://unstats.un.org/unsd/methodology/m49/overview/ | UN terms of use (free with attribution) |
| 3 | **CEPII GeoDist** `dist_cepii` (Mayer & Zignago 2011) | bilateral distances for the remoteness index | `fetch_cepii.py` | https://www.cepii.fr/distance/dist_cepii.zip | Free for research with citation; see CEPII terms (licence to confirm, see TODO) |
| 4 | **UNCTAD Liner Shipping Connectivity Index**, quarterly | shipping connectivity, 2006–2025 | `fetch_unctad.py` | https://unctadstat-api.unctad.org/bulkdownload/US.LSCI/US_LSCI | UNCTADstat terms (free with attribution) |
| 5 | **TeleGeography Submarine Cable Map** public JSON | international cables per country | `fetch_cables.py` | https://www.submarinecablemap.com/api/v3/ | TeleGeography terms (licence to confirm, see TODO) |
| 6 | **NCD-RisC** diabetes, Lancet 2024 | age-standardised diabetes prevalence 1990–2022 | `fetch_ncdrisc.py` | https://ncdrisc.org/data-downloads-diabetes.html | Free with citation of NCD-RisC (2024) |
| 7 | **IAB brain-drain data** (Brücker, Capuano & Marfouk 2013) | tertiary emigration rates, 2000 and 2010 | `fetch_iab.py` | https://doku.iab.de/daten/brain-drain/iabbd_8010_v1_emigration.xls | Free with citation |
| 8 | **CHAT** (Comin & Hobijn 2009) | adoption lags and intensity gaps | `fetch_chat.py` | https://data.nber.org/data-appendix/w15319/FinalCHAT_72909.csv | Free with citation |
| 9 | **Natural Earth** 1:50m admin-0 countries | map geometry | `fetch_naturalearth.py` | https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip | Public domain |
| 10 | **Narrative facts** (hand-curated) | Tonga outage duration, cut location | — | see [`manual/narrative_facts.csv`](manual/narrative_facts.csv) | News reports, cited in the paper |

## WDI indicator codes

`SP.POP.TOTL`, `NY.GDP.MKTP.CD`, `NY.GDP.PCAP.CD`, `NY.GDP.PCAP.PP.KD`,
`BX.TRF.PWKR.DT.GD.ZS`, `SH.MED.PHYS.ZS`, `SH.STA.DIAB.ZS`, `IT.NET.USER.ZS`,
`IT.NET.BBND.P2`, `IT.CEL.SETS.P2`, `EN.GHG.CO2.PC.CE.AR5`, `ST.INT.RCPT.XP.ZS`,
`NE.TRD.GNFS.ZS`, `EN.POP.EL5M.ZS`, `VC.IDP.NWDS`, `GOV_WGI_GE.EST` (WGI).

## Sources considered and not used

| Source | Why not |
|--------|---------|
| ND-GAIN country index | Download endpoint (`gain.nd.edu/assets/…/ndgain_countryindex_2026.zip`) returned HTTP 403 to scripted requests. |
| WorldRiskIndex (HDX, CC BY) | Downloaded and evaluated, then dropped: its exposure component scales with *absolute* population exposed, so it ranks large countries (Philippines, India, China) as most exposed and Tuvalu near the bottom. Unsuitable for a per-capita exposure comparison. |
| WHO Global Health Observatory API | Returned HTTP 500 for all requests during the build; NCD-RisC (the source behind WHO's diabetes estimates) used instead. |
| ITU broadband prices | `datahub.itu.int` returned HTTP 403 to scripted requests. |
| Docquier–Marfouk (2006) | Superseded by the IAB panel, which covers 1980–2010. |

## Processed outputs (`data/processed/`)

| File | Built by | Contents |
|------|----------|----------|
| `remoteness.csv` | `build_remoteness.py` | GDP-weighted distance to world output (km) |
| `countries.csv` | `process_countries.py` | one row per economy, all cross-sectional variables |
| `plot_countries.csv` | `process_countries.py` | pgfplots-safe subset (no quoted fields) with per-figure labels |
| `lsci_groups.csv`, `lsci_change.csv`, `lsci_hubs.csv` | `process_timeseries.py` | LSCI group medians and per-country change |
| `diabetes_groups.csv` | `process_timeseries.py` | diabetes group medians |
| `internet_groups.csv` | `process_timeseries.py` | internet and broadband medians, gaps |
| `remittances_top.csv` | `process_timeseries.py` | the 20 most remittance-dependent economies |
| `adoption.csv` | `process_adoption.py` | CHAT adoption lags and intensity gaps |
| `regression.csv`, `escape.csv` | `export_stats.py` | regression coefficients; Who Escapes table |
