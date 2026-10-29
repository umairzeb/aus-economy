"""Shared helpers: HTTP session, period/date normalisation, JSON output."""
from __future__ import annotations

import json
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "public" / "data"
CACHE_DIR = ROOT / ".cache"

USER_AGENT = "Mozilla/5.0 (compatible; aus-economy-dashboard/0.1)"

_session: requests.Session | None = None


def http() -> requests.Session:
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9",
        })
    return _session


def get(url: str, retries: int = 0, **kwargs) -> requests.Response:
    """GET with optional retries on timeouts, dropped connections and 5xx errors."""
    kwargs.setdefault("timeout", 120)
    for attempt in range(retries + 1):
        try:
            r = http().get(url, **kwargs)
            if r.status_code < 500 or attempt == retries:
                r.raise_for_status()
                return r
        except (requests.Timeout, requests.ConnectionError):
            if attempt == retries:
                raise
        time.sleep(10 * (attempt + 1))
    raise AssertionError("unreachable")


_MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def period_end(label: str) -> str:
    """Normalise a period label to the ISO date of the period's last day.

    Handles ABS periods (2026-08, 2026-Q2, 2026) and RBA dates (30-Sep-2026,
    30/09/2026). Fiscal years are ambiguous with months ("2011-12"), so they
    go through fiscal_end() instead.
    """
    s = str(label).strip()
    if m := re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", s):
        return s
    if m := re.fullmatch(r"(\d{4})-(\d{2})", s):
        return pd.Period(s, "M").end_time.date().isoformat()
    if m := re.fullmatch(r"(\d{4})-Q([1-4])", s):
        return pd.Period(f"{m[1]}Q{m[2]}", "Q").end_time.date().isoformat()
    if m := re.fullmatch(r"(\d{4})", s):
        return f"{s}-12-31"
    if m := re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", s):
        return date(int(m[3]), _MONTHS[m[2].lower()], int(m[1])).isoformat()
    if m := re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", s):
        return date(int(m[3]), int(m[2]), int(m[1])).isoformat()
    raise ValueError(f"Unrecognised period label: {label!r}")


def fiscal_end(label: str) -> str:
    """'2025-26' or '2025-26 (e)' -> '2026-06-30'."""
    m = re.match(r"(\d{4})-(\d{2})", str(label).strip())
    if not m:
        raise ValueError(f"Not a fiscal year: {label!r}")
    return f"{int(m[1]) + 1}-06-30"


def to_number(v) -> float | None:
    if v is None:
        return None
    s = str(v).strip().replace(",", "")
    if s in ("", "-", "na", "n.a.", "nan", "..", "np"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
