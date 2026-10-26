"""Commonwealth Budget Paper No. 1 tables, published as CSVs on data.gov.au
by the Department of Finance each May (Budget). The dataset name follows
'budget-YYYY-YYYY-and-portfolio-budget-statements-pbs-tables-and-data'.
"""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import date
from functools import lru_cache

from ..util import fiscal_end, get, to_number

CKAN = "https://data.gov.au/data/api/3/action/package_show"
DATASET = "budget-{y0}-{y1}-and-portfolio-budget-statements-pbs-tables-and-data"


@lru_cache(maxsize=None)
def latest() -> dict:
    """Find the newest Budget dataset and return its BP1 tables as row lists."""
    today = date.today()
    for y0 in range(today.year, today.year - 3, -1):
        name = DATASET.format(y0=y0, y1=y0 + 1)
        r = get(CKAN, params={"id": name})
        if not r.json().get("success"):
            continue
        res = [x for x in r.json()["result"]["resources"] if "Paper No.1" in x.get("name", "")]
        if not res:
            continue
        z = zipfile.ZipFile(io.BytesIO(get(res[0]["url"]).content))
        tables = {}
        for f in z.namelist():
            if f.lower().endswith(".csv"):
                text = z.read(f).decode("utf-8-sig", errors="replace")
                key = f.rsplit("/", 1)[-1].replace("CSV_Table ", "").removesuffix(".csv").strip()
                tables[key] = list(csv.reader(io.StringIO(text)))
        return {"budget_year": f"{y0}-{str(y0 + 1)[2:]}", "url": res[0]["url"],
                "dataset_url": f"https://data.gov.au/data/dataset/{name}", "tables": tables}
    raise RuntimeError("No Budget Paper No.1 tables found on data.gov.au")


def _year_rows(rows):
    """Rows whose first cell is a fiscal year like '1970-71' or '2026-27 (e)'."""
    for row in rows:
        if row and len(row[0]) >= 7 and row[0][:4].isdigit() and row[0][4] == "-":
            yield row[0].strip(), row


def history(table: str, col: int) -> tuple[list[list], str | None]:
    """Annual series from an 11.x history table. Returns (points, first_estimate_date)."""
    pts, first_est = [], None
    for label, row in _year_rows(latest()["tables"][table]):
        v = to_number(row[col]) if col < len(row) else None
        if v is None:
            continue
        d = fiscal_end(label)
        if "(e)" in label and first_est is None:
            first_est = d
        pts.append([d, v])
    return pts, first_est


def by_row(table: str, year: str) -> dict[str, float]:
    """{row label: value} for one fiscal-year column of a wide table (5.7, 6.3)."""
    rows = latest()["tables"][table]
    hdr = next(r for r in rows if year in [c.strip() for c in r])
    j = [c.strip() for c in hdr].index(year)
    out = {}
    for row in rows[rows.index(hdr) + 1:]:
        if row and row[0].strip() and j < len(row):
            v = to_number(row[j])
            if v is not None:
                out[row[0].strip()] = v
    return out
