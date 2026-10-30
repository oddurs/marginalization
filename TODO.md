# TODO

Open items. `make final` fails while any `\placeholder{}` remains in the
paper; there are currently **none**.

## Data
- [ ] **ND-GAIN**: the download returns HTTP 403 to scripts. If a manual
      download is acceptable, add the zip to `data/raw/ndgain/` (record it in the
      manifest) and add a vulnerability-vs-emissions panel as a robustness check
      for the climate figure.
- [ ] **ITU broadband prices** (% of GNI per capita): `datahub.itu.int` returns
      403. Price is the missing "intensity" measure for Section 5.
- [ ] **WHO GHO API** was returning HTTP 500; re-try for a cross-check of
      NCD-RisC diabetes and WHO workforce data.
- [ ] Confirm licences for **CEPII GeoDist** and **TeleGeography** cable data
      before any public release of processed derivatives.
- [ ] TeleGeography records branch systems under their trunk's RFS year (e.g.
      the 2026 Tonga branch of Hawaiki appears as 2018). A cables-over-time chart
      would need branch-level dates.
- [ ] CEPII GeoDist is a 2011 release with legacy codes; successor states use
      proxy distances (see `build_remoteness.py`). Taiwan carries no GDP weight.
- [ ] IAB emigration data stop in 2010. Look for a newer skilled-emigration
      source (e.g. OECD DIOC 2015/16).

## Analysis
- [ ] Robustness: remoteness with `distw` (population-weighted) instead of
      `dist`; with PPP rather than market GDP weights.
- [ ] Regression: add colonial-history and resource-rent controls; report a
      version without governance (a possible "bad control").
- [ ] Adoption analysis: measure intensity gaps at a fixed horizon after each
      technology's frontier date, so young technologies are not penalised.
- [ ] Volatility claim ("relative position, volatility and control") is argued
      but not yet measured; add growth volatility by group from WDI.

## Prose
- [ ] Section 11 mentions ship registries without a citation; add one.
- [ ] Ask a Pacific-based reviewer to read Sections 6, 7 and 10.
- [ ] `paper/draft-v0.tex` was referenced in the brief but was not in the
      repository; the sections were written fresh. Merge any preferred prose
      from the original draft.
