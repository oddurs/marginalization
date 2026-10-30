"""Check every DOI in paper/references.bib against Crossref (or doi.org).

For each entry with a `doi` field, the script fetches the Crossref record and
compares its title and first-author surname with the .bib entry. DOIs that
Crossref does not index (e.g. NBER working papers) must at least resolve at
doi.org. Exits non-zero on any mismatch so it can gate CI.
"""

from __future__ import annotations

import re
import sys
import time
import unicodedata

import requests

from _common import ROOT

BIB = ROOT / "paper" / "references.bib"


def norm(s: str) -> str:
    s = s.replace("\u2019", "'").replace("\u2018", "'")
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()
    s = re.sub(r"<[^>]+>", "", s)            # Crossref markup such as <scp>
    s = re.sub(r"\\[a-z]+|[{}]", "", s)       # LaTeX commands and braces
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def entries(text: str):
    for m in re.finditer(r"@(\w+)\{([^,]+),(.*?)\n\}", text, re.S):
        fields = dict(re.findall(r"(\w+)\s*=\s*\{(.*?)\},?\s*\n", m.group(3) + "\n", re.S))
        yield m.group(2), fields


def get(url: str) -> requests.Response:
    for attempt in range(5):
        r = requests.get(url, timeout=30, allow_redirects=False,
                         headers={"Accept": "application/json"})
        if r.status_code != 429:
            return r
        time.sleep(2 ** attempt)
    return r


def main() -> int:
    bad = 0
    for key, f in entries(BIB.read_text()):
        doi = f.get("doi")
        if not doi:
            continue
        r = get(f"https://api.crossref.org/works/{doi}")
        if r.status_code == 200:
            msg = r.json()["message"]
            title = norm(msg.get("title", [""])[0])
            ok_title = norm(f["title"])[:40] in title or title[:40] in norm(f["title"])
            first = norm(msg.get("author", [{}])[0].get("family", "")) if msg.get("author") else ""
            # Corporate authors ({{...}}) list members individually at Crossref.
            corporate = f.get("author", "").startswith("{")
            ok_author = corporate or not first or first in norm(f.get("author", ""))
            status = "ok" if ok_title and ok_author else "MISMATCH"
        else:
            r2 = requests.head(f"https://doi.org/{doi}", timeout=30, allow_redirects=False)
            status = "ok (doi.org)" if r2.status_code in (301, 302, 303) else "UNRESOLVED"
        if not status.startswith("ok"):
            bad += 1
        print(f"{status:14s} {key:22s} {doi}")
        time.sleep(0.5)
    print(f"\n{bad} problem(s)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
