"""ABS data cubes that aren't in the Data API, found via the release's "latest-release" page.

Counts of Australian Businesses (cat. 8165) is published once a year as an Excel workbook
whose URL includes the reference period, so the link is discovered from the page.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from urllib.parse import urljoin

import pandas as pd

from ..util import get

COUNTS_PAGE = ("https://www.abs.gov.au/statistics/economy/business-indicators/"
               "counts-australian-businesses-including-entries-and-exits/latest-release")
SIZE_BANDS = {"Non-employing": "No employees", "1-4": "1–4 staff", "5-19": "5–19 staff",
              "20-199": "20–199 staff", "200+": "200+ staff"}


@lru_cache(maxsize=None)
def business_counts_by_size() -> dict:
    """Table 13 (employment size ranges): one row per financial year and size band.

    Returns {url, rows: [{year, band, operating_start, entries, exits, operating_end,
    change_pct, entry_rate, exit_rate}]}.
    """
    page = get(COUNTS_PAGE, retries=2).text
    m = re.search(r'href="([^"]*8165DC01\.xlsx)"', page)
    if not m:
        raise RuntimeError("8165DC01.xlsx link not found on ABS counts page")
    url = urljoin(COUNTS_PAGE, m[1])
    df = pd.read_excel(io.BytesIO(get(url, retries=2).content), sheet_name="Table 13", header=None,
                       engine="calamine")
    header = next(i for i in range(len(df)) if str(df.iat[i, 1]).startswith("Operating at start"))
    cols = {str(c).replace("\n", "").replace(" - ", " ").strip(): j for j, c in enumerate(df.iloc[header]) if c == c}

    def col(name: str) -> int:
        return next(j for c, j in cols.items() if c.lower().startswith(name.lower()))

    rows, year = [], None
    for i in range(header + 1, len(df)):
        label = str(df.iat[i, 0]).strip()
        if re.fullmatch(r"\d{4}-\d{2}", label):
            year = label
            continue
        # The ABS uses a non-breaking hyphen ("1‑4"); normalise to match SIZE_BANDS.
        band = re.sub(r"[^\w+]+", "-", label).strip("-")
        if year and band in SIZE_BANDS:
            rows.append(dict(
                year=year, band=SIZE_BANDS[band],
                operating_start=float(df.iat[i, col("Operating at start")]),
                entries=float(df.iat[i, col("Entries Total")]),
                exits=float(df.iat[i, col("Exits Total")]),
                operating_end=float(df.iat[i, col("Operating at end")]),
                change_pct=float(df.iat[i, col("Percentage change")]),
                entry_rate=float(df.iat[i, col("Entry rate")]),
                exit_rate=float(df.iat[i, col("Exit rate")]),
            ))
    if not rows:
        raise RuntimeError("No size-band rows parsed from 8165 Table 13")
    return {"url": url, "rows": rows}
