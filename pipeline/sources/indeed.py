"""Indeed Hiring Lab job postings index for Australia (CC BY 4.0).

https://github.com/hiring-lab/job_postings_tracker - daily index of job postings on Indeed,
1 Feb 2020 = 100. Not an official statistic: it counts ads on one private job site.
"""
from __future__ import annotations

import io
from functools import lru_cache

import pandas as pd

from ..util import get

BASE = "https://raw.githubusercontent.com/hiring-lab/job_postings_tracker/master/AU/"
REPO = "https://github.com/hiring-lab/job_postings_tracker"


@lru_cache(maxsize=None)
def _csv(name: str) -> pd.DataFrame:
    df = pd.read_csv(io.StringIO(get(BASE + name, retries=2).text))
    df["date"] = pd.to_datetime(df["date"])
    return df[df["variable"] == "total postings"]


def total_postings() -> list[list]:
    """Seasonally adjusted total postings index, one point per week (the week's last day)."""
    df = _csv("aggregate_job_postings_AU.csv").set_index("date")["indeed_job_postings_index_SA"]
    weekly = df.resample("W").last().dropna()
    return [[d.date().isoformat(), round(float(v), 1)] for d, v in weekly.items()]


def by_category() -> dict:
    """Latest index by job category and its change on a year earlier."""
    df = _csv("job_postings_by_sector_AU.csv")
    latest = df["date"].max()
    ago = latest - pd.DateOffset(years=1)
    now = df[df["date"] == latest].set_index("display_name")["indeed_job_postings_index"]
    then = df[df["date"] <= ago].sort_values("date").groupby("display_name").last()["indeed_job_postings_index"]
    items = [dict(key=k, label=k, value=round(float(v), 1),
                  change_pct=round(float(v / then[k] - 1) * 100, 1) if k in then and then[k] else None)
             for k, v in now.items()]
    return {"as_of": latest.date().isoformat(), "items": sorted(items, key=lambda x: -(x["change_pct"] or -1e9))}
