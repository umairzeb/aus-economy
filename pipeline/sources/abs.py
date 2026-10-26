"""ABS Data API (SDMX REST). No API key required.

Docs: https://www.abs.gov.au/about/data-services/application-programming-interfaces-apis/data-api-user-guide
Keys are dot-separated dimension codes in the dataflow's dimension order;
an empty slot is a wildcard and '+' joins several codes.
"""
from __future__ import annotations

import io
from functools import lru_cache

import pandas as pd

from ..util import get, http, period_end

BASE = "https://data.api.abs.gov.au/rest/data"
EXPLORER = "https://explore.data.abs.gov.au/vis?df[ds]=ABS_ABS_TOPICS&df[id]={flow}&df[ag]=ABS"


class NoData(Exception):
    pass


def fetch(flow: str, key: str = "all", start: str | None = None) -> pd.DataFrame:
    params = {"format": "csv"}
    if start:
        params["startPeriod"] = start
    r = http().get(f"{BASE}/ABS,{flow}/{key}", params=params, timeout=120)
    if r.status_code == 404:
        raise NoData(f"{flow}/{key}: no records (404)")
    r.raise_for_status()
    if r.text.lstrip().startswith("NoRecordsFound"):
        raise NoData(f"{flow}/{key}: no records")
    df = pd.read_csv(io.StringIO(r.text), dtype=str)
    df["OBS_VALUE"] = pd.to_numeric(df["OBS_VALUE"], errors="coerce")
    df["date"] = df["TIME_PERIOD"].map(period_end)
    return df


def scale(df: pd.DataFrame, to_mult: int | None) -> pd.Series:
    """Rescale OBS_VALUE using UNIT_MULT (power of ten) to a target multiplier,
    e.g. to_mult=6 gives millions."""
    if to_mult is None or "UNIT_MULT" not in df:
        return df["OBS_VALUE"]
    mult = pd.to_numeric(df["UNIT_MULT"], errors="coerce").fillna(0)
    return df["OBS_VALUE"] * (10.0 ** (mult - to_mult))


@lru_cache(maxsize=None)
def codelists(flow: str) -> dict[str, dict[str, str]]:
    """{codelist id: {code: English name}} for a dataflow, e.g. CL_MERCH_COUNTRY."""
    r = get(f"https://data.api.abs.gov.au/rest/datastructure/ABS/{flow}",
            params={"references": "children"}, headers={"Accept": "application/vnd.sdmx.structure+json"})
    return {cl["id"]: {c["id"]: c["name"] for c in cl["codes"]}
            for cl in r.json()["data"].get("codelists", [])}


def series(flow: str, key: str, start: str | None = None, to_mult: int | None = None) -> list[list]:
    """Fetch exactly one time series and return [[iso_date, value], ...]."""
    df = fetch(flow, key, start)
    dims = [c for c in df.columns if c not in
            ("DATAFLOW", "TIME_PERIOD", "OBS_VALUE", "date", "UNIT_MEASURE", "UNIT_MULT",
             "OBS_STATUS", "OBS_COMMENT", "DECIMALS", "BASE_PERIOD")]
    n = len(df[dims].drop_duplicates())
    if n != 1:
        raise ValueError(f"{flow}/{key}: expected 1 series, got {n}")
    df = df.assign(v=scale(df, to_mult)).dropna(subset=["v"]).sort_values("date")
    return [[d, round(float(v), 4)] for d, v in zip(df["date"], df["v"])]
