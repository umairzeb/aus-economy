"""RBA statistical tables (CSV). https://www.rba.gov.au/statistics/tables/

Each CSV has ~10 metadata rows (Title, Description, Frequency, Units,
Source, Publication date, Series ID) followed by date rows. Tables carry
empty placeholder rows past the latest observation, and some columns are
discontinued, so always take the last non-empty value per series.
"""
from __future__ import annotations

import csv
import io
from functools import lru_cache

import pandas as pd

from ..util import get, period_end, to_number

CSV_URL = "https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv"
PAGE_URL = "https://www.rba.gov.au/statistics/tables/"


@lru_cache(maxsize=None)
def table(name: str) -> dict:
    """Return {series_id: {title, units, frequency, points}} plus '_meta'."""
    r = get(CSV_URL.format(table=name))
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig", errors="replace"))))
    header_end = next(i for i, row in enumerate(rows) if row and row[0] == "Series ID")
    meta = {row[0]: row for row in rows[:header_end + 1] if row}
    ids = meta["Series ID"]
    out = {"_meta": {"title": rows[0][0].strip(), "published": (meta.get("Publication date") or ["", ""])[1]}}
    data = [row for row in rows[header_end + 1:] if row and row[0].strip()]
    for j, sid in enumerate(ids[1:], 1):
        pts = []
        for row in data:
            v = to_number(row[j]) if j < len(row) else None
            if v is not None:
                pts.append([period_end(row[0]), v])
        out[sid] = {
            "title": meta["Title"][j].strip(),
            "units": (meta.get("Units") or [""] * (j + 1))[j].strip(),
            "frequency": (meta.get("Frequency") or [""] * (j + 1))[j].strip(),
            "points": pts,
        }
    return out


HIST_URL = "https://www.rba.gov.au/statistics/tables/xls-hist/{name}.xls"


@lru_cache(maxsize=None)
def hist_table(name: str) -> dict[str, list[list]]:
    """Frozen historical workbook (old .xls), e.g. 'f11hist-1969-2009'.

    The header row is labelled 'Series ID' or 'Mnemonic'; dates follow in column 0.
    Returns {series_id: points}.
    """
    df = pd.read_excel(io.BytesIO(get(HIST_URL.format(name=name)).content), sheet_name="Data",
                       header=None, engine="calamine")
    first = df[0].astype(str).str.strip()
    header = first[first.isin(["Series ID", "Mnemonic"])].index[0]
    ids = df.iloc[header].tolist()
    out: dict[str, list[list]] = {}
    for _, row in df.iloc[header + 1:].iterrows():
        d = pd.to_datetime(row[0], errors="coerce")
        if pd.isna(d):
            continue
        for j, sid in enumerate(ids[1:], 1):
            v = to_number(row[j])
            if isinstance(sid, str) and v is not None:
                out.setdefault(sid.strip(), []).append([d.date().isoformat(), v])
    return out


def series(table_name: str, series_id: str) -> list[list]:
    t = table(table_name)
    if series_id not in t:
        raise KeyError(f"RBA {table_name}: no series {series_id}")
    return t[series_id]["points"]
