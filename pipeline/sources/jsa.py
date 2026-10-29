"""Jobs and Skills Australia - Internet Vacancy Index (online job ads).

The workbook URL changes every month, so it is discovered from the IVI page.
"""
from __future__ import annotations

import io
import re
from urllib.parse import urljoin

import pandas as pd

from ..util import get

PAGE_URL = "https://www.jobsandskills.gov.au/data/internet-vacancy-index"
FILE_PATTERN = r'href="([^"]*anzsco2_occupations_states_and_territories[^"]*\.xlsx)"'


# jobsandskills.gov.au can be slow from cloud servers (e.g. GitHub Actions), so use
# a long read timeout with retries, and fetch once per run: a failure is remembered
# rather than retried by every builder that needs it.
TIMEOUT = (20, 120)
_result: dict | Exception | None = None


def ivi() -> dict:
    """Trend job ads for Australia by ANZSCO level. Returns {url, frame} where
    frame has columns level, code, title and one column per month (ISO end date)."""
    global _result
    if _result is None:
        try:
            _result = _fetch()
        except Exception as e:  # noqa: BLE001
            _result = e
    if isinstance(_result, Exception):
        raise _result
    return _result


def _fetch() -> dict:
    page = get(PAGE_URL, retries=2, timeout=TIMEOUT).text
    m = re.search(FILE_PATTERN, page)
    if not m:
        raise RuntimeError("IVI workbook link not found on JSA page")
    url = urljoin(PAGE_URL, m[1])
    headers = {"Accept": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*", "Referer": PAGE_URL}
    df = pd.read_excel(io.BytesIO(get(url, retries=2, timeout=TIMEOUT, headers=headers).content), sheet_name="Trend")
    df = df[df["State"].astype(str).str.upper() == "AUST"].copy()
    months = [c for c in df.columns if isinstance(c, pd.Timestamp) or hasattr(c, "year")]
    rename = {c: (pd.Timestamp(c) + pd.offsets.MonthEnd(0)).date().isoformat() for c in months}
    df = df.rename(columns=rename | {"Level": "level", "ANZSCO_CODE": "code", "Title": "title"})
    df["code"] = df["code"].astype(str)
    df["title"] = df["title"].astype(str).str.strip()
    return {"url": url, "frame": df[["level", "code", "title", *rename.values()]]}
