"""Fetch Natural Earth 1:50m admin-0 countries (public domain) for the map."""

from __future__ import annotations

from _common import RAW, download, log

URL = "https://naciscdn.org/naturalearth/50m/cultural/ne_50m_admin_0_countries.zip"


def main() -> None:
    download(URL, RAW / "naturalearth" / "ne_50m_admin_0_countries.zip")
    log("ok")


if __name__ == "__main__":
    main()
