"""Resolve country names used by different sources to ISO 3166 alpha-3 codes.

Names are matched against the UN M49 table and the World Bank economy list;
the overrides below cover spellings that appear in neither (checked by hand
against each source). Unresolved names raise, so nothing is silently dropped.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

from _common import RAW

OVERRIDES = {
    # TeleGeography
    "bahamas": "BHS", "brunei": "BRN", "cape verde": "CPV", "congo dem rep": "COD",
    "congo rep": "COG", "cote divoire": "CIV", "gambia": "GMB", "iran": "IRN",
    "micronesia": "FSM", "russia": "RUS", "south korea": "KOR", "syria": "SYR",
    "taiwan": "TWN", "tanzania": "TZA", "turkey": "TUR", "venezuela": "VEN",
    "vietnam": "VNM", "virgin islands u k": "VGB", "virgin islands u s": "VIR",
    "sint maarten": "SXM", "saint martin": "MAF", "curacao": "CUW",
    "reunion": "REU", "saint barthelemy": "BLM", "egypt": "EGY", "yemen": "YEM",
    "cook islands": "COK", "niue": "NIU", "tokelau": "TKL",
    "saint helena ascension and tristan da cunha": "SHN",
    "cocos keeling islands": "CCK", "christmas island": "CXR",
    "british indian ocean territory": "IOT", "wallis and futuna": "WLF",
    "saint pierre and miquelon": "SPM", "guernsey": "GGY", "jersey": "JEY",
    "isle of man": "IMN", "gibraltar": "GIB", "bermuda": "BMU",
    "cayman islands": "CYM", "turks and caicos islands": "TCA",
    "anguilla": "AIA", "montserrat": "MSR", "guadeloupe": "GLP",
    "martinique": "MTQ", "french guiana": "GUF", "mayotte": "MYT",
    "greenland": "GRL", "faroe islands": "FRO", "new caledonia": "NCL",
    "french polynesia": "PYF", "bonaire sint eustatius and saba": "BES",
    "libya": "LBY", "laos": "LAO", "korea": "KOR", "macedonia": "MKD",
    # IAB brain-drain
    "bahamas the": "BHS", "gambia the": "GMB", "china hong kong sar": "HKG",
    "china macao sar": "MAC", "congo dem rep of the": "COD",
    "congo rep of the": "COG", "czech republic": "CZE",
    "holy see vatican city": "VAT", "micronesia federated states of": "FSM",
    "moldova": "MDA", "occupied palestinian territory": "PSE",
    "serbia and montenegro": "SRB", "swaziland": "SWZ", "timor leste": "TLS",
    "kyrgyzstan": "KGZ", "slovakia": "SVK", "united kingdom": "GBR",
    "united states": "USA", "bolivia": "BOL", "nauru": "NRU",
}


def _key(name: str) -> str:
    s = unicodedata.normalize("NFKD", str(name)).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-z ]", " ", s.lower().replace("&", "and"))
    return re.sub(r"\s+", " ", s).strip()


def _lookup() -> dict[str, str]:
    table: dict[str, str] = {}
    m49 = pd.read_csv(RAW / "m49" / "m49.csv")
    for name, iso in zip(m49["Country or Area"], m49["ISO-alpha3 Code"]):
        if isinstance(iso, str):
            table[_key(name)] = iso
    eco = pd.read_csv(RAW / "wdi" / "economies.csv")
    for name, iso, agg in zip(eco["name"], eco["iso3"], eco["aggregate"]):
        if not agg:
            table[_key(name)] = iso
    table.update(OVERRIDES)
    return table


_TABLE: dict[str, str] | None = None


def to_iso3(name: str) -> str:
    global _TABLE
    if _TABLE is None:
        _TABLE = _lookup()
    k = _key(name)
    if k not in _TABLE:
        raise KeyError(f"unresolved country name: {name!r} (key {k!r})")
    return _TABLE[k]
