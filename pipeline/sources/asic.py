"""ASIC insolvency statistics, Series 1: companies entering external administration
(or having a controller appointed) for the first time.

Published monthly as a large workbook whose URL changes each release, so the link is
discovered from the statistics page. Table "1" lays months (Jul..Jun) down the rows and
financial years (FY20, FY21, ...) across the columns.
"""
from __future__ import annotations

import io
import re
from functools import lru_cache
from urllib.parse import urljoin

import pandas as pd

from ..util import get

PAGE_URL = "https://asic.gov.au/regulatory-resources/find-a-document/statistics/insolvency-statistics/"
FILE_PATTERN = r'href="([^"]*series-1-and-series-2[^"]*\.xlsx)"'
MONTHS = ["Jul", "Aug", "Sep", "Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun"]


@lru_cache(maxsize=None)
def companies_entering_administration() -> dict:
    """Returns {url, points: [[iso_month_end, count], ...]}."""
    page = get(PAGE_URL, retries=2).text
    m = re.search(FILE_PATTERN, page)
    if not m:
        raise RuntimeError("ASIC Series 1 workbook link not found")
    url = urljoin(PAGE_URL, m[1])
    df = pd.read_excel(io.BytesIO(get(url, retries=2).content), sheet_name="1", header=None, engine="calamine")

    header = next(i for i in range(len(df)) if "Month" in [str(v).strip() for v in df.iloc[i]])
    month_col = [str(v).strip() for v in df.iloc[header]].index("Month")
    fy_cols = {j: int(f[2:]) for j, v in enumerate(df.iloc[header]) if re.fullmatch(r"FY\d{2}", f := str(v).strip())}

    points = []
    for i in range(header + 1, len(df)):
        mon = str(df.iat[i, month_col]).strip()
        if mon == "Total":
            break
        if mon not in MONTHS:
            continue
        for j, fy in fy_cols.items():
            v = pd.to_numeric(df.iat[i, j], errors="coerce")
            if pd.isna(v):
                continue
            year = 2000 + fy - (1 if MONTHS.index(mon) < 6 else 0)  # Jul-Dec fall in the previous calendar year
            month = (MONTHS.index(mon) + 6) % 12 + 1
            points.append([pd.Period(f"{year}-{month:02d}", "M").end_time.date().isoformat(), float(v)])
    if not points:
        raise RuntimeError("No monthly values parsed from ASIC Series 1")
    return {"url": url, "points": sorted(points)}
