"""Fetch NCD-RisC age-standardised diabetes prevalence (Lancet 2024).

Country, regional and world estimates for adults 18+, 1990-2022, by sex.
"""

from __future__ import annotations

from _common import RAW, download, log

BASE = "https://ncdrisc.org/downloads/dm-2024/"
FILES = [
    "NCD_RisC_Lancet_2024_Diabetes_age_standardised_countries.csv",
    "NCD_RisC_Lancet_2024_Diabetes_age_standardised_world.csv",
]


def main() -> None:
    for f in FILES:
        download(BASE + f, RAW / "ncdrisc" / f)
    log("ok")


if __name__ == "__main__":
    main()
