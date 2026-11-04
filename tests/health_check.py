"""Health check for the data the dashboard displays.

    python -m tests.health_check            checks the files in public/data
    python -m tests.health_check --live     also compares them with the raw ABS and RBA data

FAIL means a reader could see something wrong. WARN means a person should look.
Exits 1 if the data looks wrong (the daily refresh then holds it back), 2 if something else
failed, such as overdue data or a dead link (it still publishes, and emails you), otherwise 0.
"""
from __future__ import annotations

import csv
import io
import json
import math
import re
import statistics
import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from pipeline.registry import SERIES
from pipeline.release_days import RBA_DECISIONS

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "public" / "data"
TODAY = datetime.now(timezone.utc).date()

# Days between releases and from period end to release. Overdue = age > cadence + lag + GRACE.
GRACE = 10
FRESHNESS = {
    "unemployment_rate": (31, 25), "underemployment_rate": (31, 25), "underutilisation_rate": (31, 25),
    "youth_unemployment_rate": (31, 25), "participation_rate": (31, 25), "employed_persons": (31, 25),
    "employment_change": (31, 25), "cpi_yoy": (31, 32), "trimmed_mean_yoy": (31, 32), "cpi_": (31, 32),
    "cpi_yoy_q": (92, 32), "trimmed_mean_yoy_q": (92, 32), "wpi_yoy": (92, 50), "real_wage_growth": (92, 50),
    "job_vacancies": (92, 40), "gdp_": (92, 70), "terms_of_trade": (92, 70), "household_saving_ratio": (92, 70),
    "exports_services": (92, 70), "imports_services": (92, 70), "exports_education": (92, 70),
    "trade_balance": (31, 40), "exports_goods": (31, 40), "imports_goods": (31, 40), "household_spending_yoy": (31, 40),
    "dwelling_approvals": (31, 40), "dwelling_mean_price": (92, 100), "lending_owner": (92, 45),
    "lending_investor": (92, 45), "lending_first": (92, 45), "lending_small": (92, 45), "lending_medium": (92, 45),
    "mortgage_rate": (31, 35), "household_debt_to_income": (92, 100), "bond_10y": (31, 35), "aud_": (31, 10),
    "money_": (31, 35), "credit_": (31, 35), "business_rate": (31, 65), "insolvencies": (31, 40),
    "job_postings_indeed": (7, 10), "population": (92, 175), "nom_": (92, 175), "natural_increase": (92, 175),
}
BUNDLE_FRESHNESS = {
    "cpi_breakdown": (31, 32), "dwelling_price_by_state": (92, 100), "exports_by_commodity": (31, 45),
    "exports_by_country": (31, 45), "gdp_by_industry": (92, 70), "job_postings_by_category": (7, 12),
    "job_vacancies_by_industry": (92, 40), "population_by_state": (92, 175), "unemployment_by_state": (31, 25),
}
# Where a latest reading outside these limits means the data is wrong, not that the economy moved.
LIMITS = {
    "unemployment_rate": (2, 12), "underemployment_rate": (3, 15), "participation_rate": (60, 72), "cpi_yoy": (-2, 12),
    "trimmed_mean_yoy": (-1, 10), "wpi_yoy": (0.5, 8), "cash_rate": (0, 12), "mortgage_rate_variable": (3, 14),
    "mortgage_rate_discounted": (2, 12), "gdp_growth_yoy": (-8, 10), "aud_usd": (0.45, 1.1), "bond_10y": (0.5, 10),
    "population": (2.6e7, 3.1e7), "dwelling_mean_price": (700, 1600), "household_debt_to_income": (120, 230),
    "insolvencies_12m": (3000, 30000), "job_postings_indeed": (70, 250), "terms_of_trade": (50, 150),
    "business_rate_small": (3, 14), "business_rate_large": (2, 12), "money_m3_growth": (-5, 20),
    "credit_housing_growth": (-2, 20), "dwelling_approvals_12m": (100000, 300000), "cpi_rents_yoy": (-3, 15),
}


@dataclass
class Result:
    group: str
    name: str
    status: str
    detail: str = ""


results: list[Result] = []


def record(group: str, name: str, ok: bool, detail: str = "", level: str = "FAIL") -> None:
    results.append(Result(group, name, "PASS" if ok else level, "" if ok else detail))


def load(kind: str) -> dict[str, dict]:
    return {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((DATA / kind).glob("*.json"))}


def close(a: float, b: float, tol: float) -> bool:
    return abs(a - b) <= tol


def period_age(iso: str) -> int:
    return (TODAY - date.fromisoformat(iso)).days


def actuals(s: dict) -> list:
    fc = s.get("forecast_from")
    return [p for p in s["points"] if not fc or p[0] < fc]


def future_dated(s: dict, today: date) -> bool:
    """An actual figure dated ahead of today. RBA decisions carry the date they take effect,
    the day after the announcement, so those may be a little ahead."""
    limit = today + timedelta(days=2 if s["freq"] == "event" else 0)
    return any(d > limit.isoformat() for d, _ in actuals(s))


def fy_end(label: str) -> str:
    return f"{int(label[:4]) + 1}-06-30"


# --- 1. Structure -------------------------------------------------------------------------

def check_structure(series: dict, bundles: dict) -> None:
    g = "1 Structure"
    for sid, s in series.items():
        pts = s.get("points") or []
        problems = []
        if not pts:
            problems.append("no points")
        if any(k not in s for k in ("id", "title", "unit", "freq", "source", "updated")):
            problems.append("missing fields")
        if s.get("id") != sid:
            problems.append(f"id is {s.get('id')}")
        dates = [p[0] for p in pts]
        if dates != sorted(dates):
            problems.append("dates out of order")
        if len(dates) != len(set(dates)):
            problems.append("duplicate dates")
        if any(not isinstance(p[1], (int, float)) or not math.isfinite(p[1]) for p in pts):
            problems.append("non-numeric value")
        if any(not re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) for d in dates):
            problems.append("bad date")
        if future_dated(s, TODAY):
            problems.append("actual dated in the future")
        record(g, f"series {sid}", not problems, ", ".join(problems))
    for bid, b in bundles.items():
        problems = []
        if not b.get("items"):
            problems.append("no items")
        for i in b.get("items", []):
            if not i.get("label") or not isinstance(i.get("value"), (int, float)) or not math.isfinite(i["value"]):
                problems.append(f"bad item {i.get('key')}")
        if len({i.get("key") for i in b.get("items", [])}) != len(b.get("items", [])):
            problems.append("duplicate keys")
        record(g, f"bundle {bid}", not problems, ", ".join(problems))

    # Everything the page asks for exists; everything in the registry was written.
    app = (ROOT / "src" / "App.tsx").read_text(encoding="utf-8")
    wanted = re.findall(r'"([a-z0-9_]+)"', app[app.index("const SERIES"):app.index("const BUNDLES")])
    missing = [w for w in wanted if w not in series]
    record(g, "every series the page requests has a file", not missing, str(missing))
    body = app[app.index("const BUNDLES"):]
    wanted_b = re.findall(r'"([a-z0-9_]+)"', body[:body.index("];")])
    missing = [w for w in wanted_b if w not in bundles]
    record(g, "every bundle the page requests has a file", not missing, str(missing))
    missing = [x["id"] for x in SERIES if x["id"] not in series]
    record(g, "every registered series has a file", not missing, str(missing))
    src = "".join(f.read_text(encoding="utf-8") for f in (ROOT / "src").rglob("*.ts*"))
    used = set(re.findall(r"\bS\.([a-z0-9_]+)", src))
    missing = sorted(u for u in used if u not in wanted)
    record(g, "every series used in the code is requested by the page", not missing, str(missing))


# --- 2. Freshness -------------------------------------------------------------------------

def check_freshness(series: dict, bundles: dict, manifest: dict) -> None:
    g = "2 Freshness"
    for sid, s in series.items():
        if s["freq"] in ("event", "FY"):
            continue
        rule = FRESHNESS.get(sid) or next((v for k, v in sorted(FRESHNESS.items(), key=lambda kv: -len(kv[0])) if sid.startswith(k)), None)
        if rule is None:
            record(g, f"{sid} has a freshness rule", False, "no rule")
            continue
        last = actuals(s)[-1][0]
        limit = rule[0] + rule[1] + GRACE
        age = period_age(last)
        record(g, f"{sid} up to date", age <= limit, f"latest {last}, {age} days old, limit {limit}")
    for bid, (cadence, lag) in BUNDLE_FRESHNESS.items():
        b = bundles.get(bid)
        if b:
            age = period_age(b["as_of"])
            record(g, f"bundle {bid} up to date", age <= cadence + lag + GRACE, f"as of {b['as_of']}, {age} days old")

    # Budget: the year just ended should have a final result once the Final Budget Outcome is out (late Sept).
    bal = series["budget_balance_pct_gdp"]
    fc = bal.get("forecast_from")
    ended = f"{TODAY.year if TODAY.month > 9 else TODAY.year - 1}-06-30"
    record(g, "budget history includes the latest finished financial year", bool(fc) and fc > ended,
           f"forecasts start {fc}, but the year to {ended} has finished: add its Final Budget Outcome to BUDGET_OUTCOMES in pipeline/registry.py")
    # Budget Paper data is yearly (May).
    rev = bundles["revenue_mix"]
    y0 = int(rev["as_of"][:4])
    expected = TODAY.year if TODAY.month >= 6 else TODAY.year - 1
    record(g, "bundles use the latest Budget", y0 >= expected, f"using {rev['as_of']}")

    upcoming = [d for d in RBA_DECISIONS if d >= TODAY]
    record(g, "the release-day schedule has an upcoming RBA decision", bool(upcoming) and (upcoming[0] - TODAY).days <= 120,
           f"next listed is {upcoming[0] if upcoming else 'none'}: add new dates to RBA_DECISIONS in pipeline/release_days.py")

    gen = datetime.fromisoformat(manifest["generated"])
    hours = (datetime.now(timezone.utc) - gen).total_seconds() / 3600
    record(g, "pipeline ran in the last 36 hours", hours <= 36, f"last run {manifest['generated']}", level="WARN")
    # One bad day keeps the last good data; the pipeline itself fails the run after two weeks.
    record(g, "manifest reports no source errors", not manifest.get("errors"), str(manifest.get("errors"))[:300], level="WARN")
    record(g, "manifest reports no warnings", not manifest.get("warnings"), str(manifest.get("warnings"))[:300], level="WARN")
    record(g, "manifest reports no stale files", not manifest.get("stale"), str(manifest.get("stale"))[:300], level="WARN")


# --- Source links ---------------------------------------------------------------------------

def check_links(series: dict, bundles: dict) -> None:
    g = "6 Source links"
    shown = {k: v for k, v in series.items() if not v.get("hidden")} | bundles
    urls = {x["source"]["url"]: k for k, x in shown.items()}
    placeholder = [k for u, k in urls.items() if "<" in u or u.rstrip("/").endswith("/rest/data")]
    record(g, "no source link is a placeholder or incomplete address", not placeholder, str(placeholder))
    raw = [k for u, k in urls.items() if "data.api.abs.gov.au" in u or u.endswith((".csv", ".xlsx"))]
    record(g, "source links open a readable page, not a raw data file", not raw, f"{len(raw)} open raw data, e.g. {raw[:3]}")
    if "--live" in sys.argv:
        for u, k in urls.items():
            try:
                code = requests.get(u, headers={"User-Agent": "Mozilla/5.0"}, timeout=40, allow_redirects=True, stream=True).status_code
            except requests.RequestException as e:
                code = str(e)[:80]
            # RBA turns away scripts from some networks but opens fine in a browser.
            level = "WARN" if "rba.gov.au" in u else "FAIL"
            record(g, f"link opens: {u}", code == 200, f"{code} ({k})", level=level)


# --- 3. Plausibility ----------------------------------------------------------------------

def check_plausibility(series: dict) -> None:
    g = "3 Plausibility"
    for sid, (lo, hi) in LIMITS.items():
        v = actuals(series[sid])[-1][1]
        record(g, f"{sid} latest within sane limits", lo <= v <= hi, f"{v} outside {lo}..{hi}")
    for sid, s in series.items():
        pts = actuals(s)
        if s["freq"] == "event" or len(pts) < 24:
            continue
        vals = [p[1] for p in pts]
        moves = [abs(b - a) for a, b in zip(vals, vals[1:])]
        typical = statistics.median(moves[-60:]) or statistics.mean(moves[-60:]) or 1e-9
        recent = moves[-3:]
        # Original (not seasonally adjusted) and yearly-change series move more, so this only warns.
        if max(recent) > typical * 8:
            record(g, f"{sid} no sudden jump in latest figures", False,
                   f"latest moves {[round(x, 2) for x in recent]}, typical {round(typical, 3)}", level="WARN")
        else:
            record(g, f"{sid} no sudden jump in latest figures", True)
        tail = vals[-6:]
        record(g, f"{sid} not frozen", len(set(tail)) > 1 or s["freq"] == "FY", f"last 6 values all {tail[0]}", level="WARN")


# --- 4. Do the numbers agree with each other? ---------------------------------------------

def check_relations(series: dict, bundles: dict) -> None:
    g = "4 Consistency"
    S = {k: dict((d, v) for d, v in s["points"]) for k, s in series.items()}

    def latest_pairs(a: str, b: str, n: int = 12) -> list[str]:
        return sorted(set(S[a]) & set(S[b]))[-n:]

    def rel(name: str, dates: list[str], fn, tol: float) -> None:
        bad = [(d, round(fn(d), 3)) for d in dates if abs(fn(d)) > tol]
        record(g, name, not bad and bool(dates), f"off by more than {tol}: {bad[:4]}" if dates else "nothing to compare")

    rel("underutilisation = unemployment + underemployment", latest_pairs("unemployment_rate", "underemployment_rate"),
        lambda d: S["underutilisation_rate"][d] - S["unemployment_rate"][d] - S["underemployment_rate"][d], 0.1)
    rel("goods balance = exports - imports", latest_pairs("exports_goods", "imports_goods"),
        lambda d: S["trade_balance_goods"][d] - (S["exports_goods"][d] - S["imports_goods"][d]), 2)
    rel("real wages = wages - prices", latest_pairs("wpi_yoy", "cpi_yoy_q"),
        lambda d: S["real_wage_growth"][d] - (S["wpi_yoy"][d] - S["cpi_yoy_q"][d]), 0.11)
    rel("population growth about = GDP growth - per person growth", latest_pairs("gdp_growth_yoy", "gdp_per_capita_growth_yoy"),
        lambda d: S["gdp_growth_yoy"][d] - S["gdp_per_capita_growth_yoy"][d] - S["population_growth_yoy"].get(d, S["population_growth_yoy"][max(S["population_growth_yoy"])]), 0.7)

    def recompute_sum(target: str, source: str, n: int, scale: float, tol: float) -> None:
        pts = series[source]["points"]
        bad = []
        for i in range(max(n - 1, len(pts) - 12), len(pts)):
            d = pts[i][0]
            if d in S[target]:
                v = sum(p[1] for p in pts[i - n + 1:i + 1]) * scale
                if abs(v - S[target][d]) > tol:
                    bad.append((d, round(v, 2), S[target][d]))
        record(g, f"{target} matches its monthly or quarterly figures", not bad, str(bad[:3]))

    recompute_sum("trade_balance_12m", "trade_balance_goods", 12, 1 / 1000, 0.06)
    recompute_sum("dwelling_approvals_12m", "dwelling_approvals_m", 12, 1, 1)
    recompute_sum("insolvencies_12m", "insolvencies_m", 12, 1, 1)
    recompute_sum("lending_small_business_12m", "lending_small_business_q", 4, 1 / 1000, 0.06)
    recompute_sum("lending_medium_business_12m", "lending_medium_business_q", 4, 1 / 1000, 0.06)
    recompute_sum("exports_education_4q", "exports_education_q", 4, 1 / 1000, 0.06)
    recompute_sum("nom_annual", "nom_q", 4, 1, 1)
    recompute_sum("natural_increase_annual", "natural_increase_q", 4, 1, 1)

    def yoy_of(target: str, source: str, lag: int, tol: float) -> None:
        pts = series[source]["points"]
        bad = []
        for i in range(max(lag, len(pts) - 8), len(pts)):
            v = (pts[i][1] / pts[i - lag][1] - 1) * 100
            d = pts[i][0]
            if d in S[target] and abs(v - S[target][d]) > tol:
                bad.append((d, round(v, 2), S[target][d]))
        record(g, f"{target} is the yearly change in {source}", not bad, str(bad[:3]))

    yoy_of("gdp_growth_yoy", "gdp_real", 4, 0.06)
    yoy_of("gdp_per_capita_growth_yoy", "gdp_per_capita_real", 4, 0.06)
    yoy_of("population_growth_yoy", "population", 4, 0.006)
    yoy_of("money_m1_growth", "money_m1", 12, 0.06)

    # Inflation: three of the displayed numbers describe nearly the same thing.
    m = S["cpi_yoy"]
    q_date = max(S["cpi_yoy_q"])
    months = sorted(d for d in m if d <= q_date)[-3:]
    avg = statistics.mean(m[d] for d in months)
    record(g, "quarterly inflation is close to the average of its three months", close(avg, S["cpi_yoy_q"][q_date], 0.3),
           f"quarter {S['cpi_yoy_q'][q_date]}, months average {round(avg, 2)}")

    # Bundles
    def shares(bid: str, target: float, tol: float) -> None:
        b = bundles[bid]
        total = sum(i.get("share", 0) for i in b["items"])
        record(g, f"{bid} shares add up to {target}%", close(total, target, tol), f"they add up to {round(total, 1)}%")

    def totals(bid: str, tol: float) -> None:
        b = bundles[bid]
        total = sum(i["value"] for i in b["items"])
        record(g, f"{bid} items add up to the stated total", close(total, b["total"], tol), f"{round(total, 1)} vs {b['total']}")

    shares("revenue_mix", 100, 0.5)
    totals("revenue_mix", 0.6)
    shares("spending_by_function", 100, 0.5)
    totals("spending_by_function", 1)
    shares("gdp_by_industry", 100, 1)
    excise = next(i for i in bundles["revenue_mix"]["items"] if i["key"] == "excise")
    total_parts = sum(p["value"] for p in excise["parts"])
    record(g, "excise products add up to the excise bar", close(total_parts, excise["value"], 0.3), f"{round(total_parts, 1)} vs {excise['value']}")
    for bid in ("exports_by_commodity", "exports_by_country"):
        b = bundles[bid]
        s12 = sum(p[1] for p in series["exports_goods"]["points"][-12:]) / 1000
        record(g, f"{bid} total is close to 12 months of goods exports", abs(b["total"] / s12 - 1) < 0.05,
               f"{b['total']} vs {round(s12, 1)} (original vs seasonally adjusted)", level="WARN")
        over = sum(i.get("share", 0) for i in b["items"])
        record(g, f"{bid} shares don't exceed 100%", over <= 100.5, f"{round(over, 1)}%")

    pop = bundles["population_by_state"]
    total = sum(i["value"] for i in pop["items"])
    record(g, "state populations add up to the national figure", abs(total / S["population"][pop["as_of"]] - 1) < 0.002,
           f"{total:,.0f} vs {S['population'][pop['as_of']]:,.0f}")

    ur = bundles["unemployment_by_state"]
    vals = [i["value"] for i in ur["items"]]
    nat = S["unemployment_rate"][ur["as_of"]]
    record(g, "national unemployment sits within the state range", min(vals) <= nat <= max(vals), f"{nat} vs {min(vals)}..{max(vals)}")

    states = bundles["dwelling_price_by_state"]
    vals = [i["value"] for i in states["items"]]
    nat = S["dwelling_mean_price"][states["as_of"]]
    record(g, "national home price sits within the state range", min(vals) <= nat <= max(vals), f"{nat} vs {min(vals)}..{max(vals)}")

    size = bundles["business_counts_by_size"]
    bad = []
    for i in size["items"]:
        for k in ("entry_rate", "exit_rate"):
            if not 0 <= i.get(k, -1) <= 60:
                bad.append((i["label"], k, i.get(k)))
    record(g, "business entry and exit rates are sensible", not bad, str(bad))

    small, large = S["business_rate_small"], S["business_rate_large"]
    d = max(small)
    record(g, "small businesses pay more than large ones", small[d] > large[d], f"{small[d]} vs {large[d]}", level="WARN")
    record(g, "discounted mortgage rate is below the standard rate", S["mortgage_rate_discounted"][max(S["mortgage_rate_discounted"])] < S["mortgage_rate_variable"][max(S["mortgage_rate_variable"])], "")
    cash = series["cash_rate"]["points"][-1][1]
    record(g, "mortgage rates sit above the cash rate", S["mortgage_rate_discounted"][max(S["mortgage_rate_discounted"])] > cash, "")


# --- Published figures --------------------------------------------------------------------

PUBLISHED = [
    # (series, date, value, tolerance, where it was published). A revision can move these, so they warn.
    ("unemployment_rate", "2026-09-30", 4.7, 0.05, "ABS Labour Force, Sep 2026"),
    ("employed_persons", "2026-09-30", 14782.7, 0.1, "ABS Labour Force, Sep 2026"),
    ("employment_change", "2026-09-30", -39.3, 0.1, "ABS Labour Force, Sep 2026"),
    ("cpi_yoy", "2026-09-30", 4.3, 0.05, "ABS CPI, Sep 2026"),
    ("trimmed_mean_yoy", "2026-09-30", 3.6, 0.05, "ABS CPI, Sep 2026"),
    ("wpi_yoy", "2026-06-30", 3.2, 0.05, "ABS WPI, Jun qtr 2026"),
    ("gdp_growth_yoy", "2026-06-30", 2.1, 0.05, "ABS National Accounts, Jun qtr 2026"),
    ("gdp_per_capita_growth_yoy", "2026-06-30", 0.7, 0.05, "ABS National Accounts, Jun qtr 2026"),
    ("dwelling_mean_price", "2026-06-30", 1100.4, 0.1, "ABS Total Value of Dwellings, Jun qtr 2026"),
    ("job_vacancies", "2026-09-30", 325.0, 0.1, "ABS Job Vacancies, Aug 2026"),
    ("cash_rate", "2026-09-30", 4.6, 0.001, "RBA decision, 29 Sep 2026"),
]


def check_published(series: dict, bundles: dict) -> None:
    g = "7 Matches published releases"
    for sid, d, want, tol, where in PUBLISHED:
        got = dict(map(tuple, series[sid]["points"])).get(d)
        record(g, f"{sid} at {d} matches {where}", got is not None and abs(got - want) <= tol, f"dashboard {got}, published {want}", level="WARN")
    ins = dict(map(tuple, series["insolvencies_m"]["points"]))
    fy = sum(v for k, v in ins.items() if "2025-07" <= k[:7] <= "2026-06")
    record(g, "ASIC 2025-26 total matches ASIC's published 14,153", fy == 14153, f"dashboard {fy}", level="WARN")
    size = bundles["business_counts_by_size"]["items"]
    for key, want in (("value", 2814778), ("entries", 460461), ("exits", 375331)):
        got = sum(i.get(key, 0) for i in size)
        record(g, f"business {key} add up to the ABS published {want:,}", got == want, f"dashboard {got}", level="WARN")
    bal = series["budget_balance"]
    got = dict(map(tuple, bal["points"])).get("2026-06-30")
    record(g, "2025-26 budget result matches the Final Budget Outcome (-$22.3bn)", got is not None and abs(got + 22300) < 100,
           f"dashboard {got} $m, marked as a forecast from {bal.get('forecast_from')}", level="WARN")


# --- 5. Displayed figures against the raw source ------------------------------------------

def raw_abs(flow: str, key: str, to_mult, negate: bool) -> dict[str, float]:
    r = requests.get(f"https://data.api.abs.gov.au/rest/data/ABS,{flow}/{key}", params={"format": "csv", "startPeriod": "2023"}, timeout=120)
    r.raise_for_status()
    out = {}
    for row in csv.DictReader(io.StringIO(r.text)):
        if row.get("OBS_VALUE") in ("", None):
            continue
        v = float(row["OBS_VALUE"])
        if to_mult is not None and row.get("UNIT_MULT"):
            v *= 10.0 ** (float(row["UNIT_MULT"]) - to_mult)
        out[row["TIME_PERIOD"]] = -v if negate else v
    return out


def period_key(iso: str, freq: str) -> list[str]:
    y, m = iso[:4], int(iso[5:7])
    return [f"{y}-{m:02d}", f"{y}-Q{(m + 2) // 3}"] if freq in ("M", "Q") else [iso]


def check_live(series: dict) -> None:
    g = "5 Matches the source"
    session_headers = {"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"}
    rba_cache: dict[str, dict] = {}
    for spec in SERIES:
        s = series.get(spec["id"])
        if s is None:
            continue
        name = f"{spec['id']} matches the source"
        try:
            if "abs" in spec:
                raw = raw_abs(*spec["abs"], spec.get("to_mult"), spec.get("negate", False))
                pairs = []
                for d, v in s["points"][-24:]:
                    key = next((k for k in period_key(d, s["freq"]) if k in raw), None)
                    if key:
                        pairs.append((d, v, raw[key]))
            else:
                table, sid = spec["rba"]
                if table not in rba_cache:
                    r = requests.get(f"https://www.rba.gov.au/statistics/tables/csv/{table}-data.csv", headers=session_headers, timeout=60)
                    r.raise_for_status()
                    rba_cache[table] = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig", errors="replace"))))
                rows = rba_cache[table]
                head = next(i for i, x in enumerate(rows) if x and x[0] == "Series ID")
                j = rows[head].index(sid)
                vals = [(x[0], x[j]) for x in rows[head + 1:] if len(x) > j and x[j].strip()]
                latest = float(vals[-1][1])
                pairs = [(s["points"][-1][0], s["points"][-1][1], latest)]
            bad = [p for p in pairs if abs(p[1] - p[2]) > max(0.0006, abs(p[2]) * 1e-5)]
            newer = "abs" in spec and bool(raw) and max(raw) not in period_key(s["points"][-1][0], s["freq"]) and max(raw) > s["points"][-1][0][:7]
            if newer:
                # A new release also revises earlier months, so differences here aren't bad data.
                record(g, f"{spec['id']} has the newest period the source offers", False,
                       f"source has {max(raw)}, dashboard has {s['points'][-1][0]}; the next refresh picks it up", level="WARN")
            else:
                record(g, name, bool(pairs) and not bad, f"{len(bad)} of {len(pairs)} differ, e.g. {bad[:2]}" if pairs else "no shared dates")
        except requests.HTTPError as e:
            record(g, name, False, f"could not fetch: {e}"[:160], level="WARN")


# --- Report -------------------------------------------------------------------------------

def main() -> int:
    series, bundles = load("series"), load("bundles")
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    check_structure(series, bundles)
    check_freshness(series, bundles, manifest)
    check_plausibility(series)
    check_relations(series, bundles)
    check_links(series, bundles)
    check_published(series, bundles)
    if "--live" in sys.argv:
        check_live(series)

    groups = sorted({r.group for r in results})
    for g in groups:
        rs = [r for r in results if r.group == g]
        counts = {k: sum(r.status == k for r in rs) for k in ("PASS", "WARN", "FAIL")}
        print(f"\n{g}: {counts['PASS']} pass, {counts['WARN']} warn, {counts['FAIL']} fail")
        for r in rs:
            if r.status != "PASS":
                print(f"  {r.status}  {r.name}: {r.detail}")
    fails = [r for r in results if r.status == "FAIL"]
    warns = sum(r.status == "WARN" for r in results)
    print(f"\nTotal: {len(results)} checks, {len(results) - len(fails) - warns} pass, {warns} warn, {len(fails)} fail")
    if any(r.group[0] in "134" for r in fails):
        return 1
    return 2 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
