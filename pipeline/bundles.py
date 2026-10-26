"""Bundles: cross-sections for bar charts and tables (who we export to, where
the budget goes, unemployment by state). Each returns
{id, title, unit, section, as_of, source, items: [{key, label, value, ...}]}.
"""
from __future__ import annotations

from datetime import date

import pandas as pd

from .derived import BUDGET, JSA, abs_src
from .registry import CPI_COMPONENTS, STATES
from .sources import abs as abs_
from .sources import budget, jsa

STATE_CODES = "+".join(STATES)


def _start(months: int) -> str:
    p = pd.Period(date.today(), "M") - months
    return str(p)


SHORT_LABELS = {
    "CHIN": "China", "RKOR": "South Korea", "USA": "United States", "HONG": "Hong Kong", "UK": "United Kingdom",
    "281": "Iron ore", "971": "Gold", "321": "Coal", "343": "Natural gas (LNG)", "011": "Beef",
    "041": "Wheat", "285": "Alumina & aluminium ores", "333": "Crude oil", "278": "Crude minerals n.e.s.",
    "287": "Copper & other base metal ores", "012": "Lamb, pork & other meat", "682": "Copper",
    "684": "Aluminium", "057": "Fruit & nuts", "112": "Alcoholic beverages (mostly wine)",
}


def _short(code: str, name: str) -> str:
    if code in SHORT_LABELS:
        return SHORT_LABELS[code]
    return name.split(" (")[0].split(", whether")[0].removesuffix(", nfd")


def _top_exports(by: str, keep, label_list: str, limit: int, title: str, bid: str, notes: str) -> dict:
    key = "TOT..TOT.M" if by == "COUNTRY_DEST" else ".TOT.TOT.M"
    df = abs_.fetch("MERCH_EXP", key, start=_start(26))
    df["v"] = abs_.scale(df, 6)
    last = sorted(df["date"].unique())
    recent, prior = last[-12:], last[-24:-12]
    if len(prior) < 12:
        raise ValueError("MERCH_EXP: fewer than 24 months returned")
    cur = df[df["date"].isin(recent)].groupby(by)["v"].sum()
    old = df[df["date"].isin(prior)].groupby(by)["v"].sum()
    total = cur.get("TOT")
    names = abs_.codelists("MERCH_EXP")[label_list]
    rows = cur[[k for k in cur.index if keep(k)]].sort_values(ascending=False).head(limit)
    items = [dict(key=k, label=_short(k, names.get(k, k)), full_label=names.get(k, k),
                  value=round(v / 1000, 2), share=round(v / total * 100, 1),
                  change_pct=round((v / old[k] - 1) * 100, 1) if old.get(k) else None)
             for k, v in rows.items()]
    return dict(id=bid, title=title, unit="$bn (12 months)", section="trade",
                as_of=recent[-1], period=f"{recent[0][:7]} to {recent[-1][:7]}",
                total=round(total / 1000, 1), items=items, notes=notes,
                source=abs_src("MERCH_EXP", key))


def exports_by_country() -> dict:
    return _top_exports("COUNTRY_DEST", lambda k: k != "TOT", "CL_MERCH_COUNTRY", 12,
                        "Who buys Australia's goods", "exports_by_country",
                        "Merchandise (goods) exports only; services such as education and tourism are excluded. "
                        "change_pct compares with the previous 12 months.")


def exports_by_commodity() -> dict:
    return _top_exports("COMMODITY_SITC", lambda k: len(k) == 3 and k != "TOT", "CL_MERCH_SITC", 15,
                        "What Australia sells overseas (goods)", "exports_by_commodity",
                        "SITC 3-digit commodity groups. change_pct compares with the previous 12 months.")


INDUSTRIES = {
    "A": "Agriculture, forestry & fishing", "B": "Mining", "C": "Manufacturing",
    "D": "Electricity, gas, water & waste", "E": "Construction", "F": "Wholesale trade", "G": "Retail trade",
    "H": "Accommodation & food", "I": "Transport, postal & warehousing", "J": "Media & telecommunications",
    "K": "Financial & insurance services", "L": "Rental, hiring & real estate",
    "M": "Professional, scientific & technical", "N": "Administrative & support", "O": "Public administration & safety",
    "P": "Education & training", "Q": "Health care & social assistance", "R": "Arts & recreation",
    "S": "Other services",
}


def gdp_by_industry() -> dict:
    key = f"VCH.GPM.SSS.20.{'+'.join(INDUSTRIES)}.AUS.Q"
    df = abs_.fetch("ANA_IND_GVA", key, start=_start(30))
    last4 = sorted(df["date"].unique())[-4:]
    cur = df[df["date"].isin(last4)].groupby("INDUSTRY")["OBS_VALUE"].sum()
    total = cur.sum()
    items = [dict(key=k, label=INDUSTRIES.get(k, k), value=round(v / 1000, 1), share=round(v / total * 100, 1))
             for k, v in cur.sort_values(ascending=False).items()]
    return dict(id="gdp_by_industry", title="What the economy produces (by industry)", unit="$bn (12 months)",
                section="growth", as_of=last4[-1], items=items, source=abs_src("ANA_IND_GVA", key),
                notes="Gross value added, chain volume measures, last four quarters. Shares are approximate "
                      "because chain volume components are not strictly additive. Excludes ownership of "
                      "dwellings and taxes on products.")


def revenue_mix() -> dict:
    b = budget.latest()
    year = b["budget_year"]
    r = budget.by_row("5.7", year)
    parts = [("individuals", "Income tax on individuals", r["Total individuals and other withholding tax"]),
             ("company", "Company tax", r["Company tax"]),
             ("gst", "GST", r["Goods and services tax"]),
             ("super", "Superannuation fund taxes", r["Superannuation fund taxes"]),
             ("excise", "Fuel, alcohol & tobacco excise, customs", r["Total excise and customs duty"])]
    other_tax = r["Taxation receipts"] - sum(p[2] for p in parts)
    parts += [("other_tax", "Other taxes", other_tax), ("non_tax", "Non-tax receipts", r["Non-taxation receipts"])]
    total = r["Total receipts"]
    items = [dict(key=k, label=lbl, value=round(v / 1000, 1), share=round(v / total * 100, 1)) for k, lbl, v in parts]
    return dict(id="revenue_mix", title=f"Where the government's money comes from ({year} Budget estimate)",
                unit="$bn", section="budget", as_of=year, total=round(total / 1000, 1), items=items,
                source={"name": BUDGET, "dataset": f"Budget {year}, Table 5.7", "url": b["dataset_url"]})


def spending_by_function() -> dict:
    b = budget.latest()
    year = b["budget_year"]
    r = budget.by_row("6.3", year)
    total = r.pop("Total expenses")
    items = [dict(key=k.lower().replace(" ", "_").replace(",", ""), label=k, value=round(v / 1000, 1),
                  share=round(v / total * 100, 1)) for k, v in sorted(r.items(), key=lambda kv: -kv[1])]
    return dict(id="spending_by_function", title=f"Where the government's money goes ({year} Budget estimate)",
                unit="$bn", section="budget", as_of=year, total=round(total / 1000, 1), items=items,
                source={"name": BUDGET, "dataset": f"Budget {year}, Table 6.3", "url": b["dataset_url"]},
                notes="Accrual expenses. 'Other purposes' is mostly GST paid to the states and interest on debt.")


def cpi_breakdown(got) -> dict:
    items = []
    for slug, (_, label) in CPI_COMPONENTS.items():
        pts = got(f"cpi_{slug}_yoy")
        if pts:
            items.append(dict(key=slug, label=label, value=pts[-1][1], as_of=pts[-1][0]))
    items.sort(key=lambda x: -x["value"])
    return dict(id="cpi_breakdown", title="What's getting more expensive", unit="% y/y", section="prices",
                as_of=max(i["as_of"] for i in items), items=items,
                source=abs_src("CPI", "3.<groups>.10.50.M"),
                notes="Annual price change by category, latest month. Compare with headline CPI.")


def _by_state(flow: str, key: str, bid: str, title: str, unit: str, section: str, change_lag: int,
              to_mult: int | None = None, change: str = "pct", nd: int = 1) -> dict:
    df = abs_.fetch(flow, key, start=_start(36))
    df["v"] = abs_.scale(df, to_mult)
    items = []
    for code, abbr in STATES.items():
        g = df[df["REGION"] == code].sort_values("date")
        if g.empty:
            continue
        v, prev = g["v"].iloc[-1], g["v"].iloc[-1 - change_lag] if len(g) > change_lag else None
        ch = None if prev is None else (round((v / prev - 1) * 100, 1) if change == "pct" else round(v - prev, 1))
        items.append(dict(key=abbr, label=abbr, value=round(float(v), nd), change=ch, as_of=g["date"].iloc[-1]))
    return dict(id=bid, title=title, unit=unit, section=section, as_of=max(i["as_of"] for i in items),
                change_unit="% vs a year ago" if change == "pct" else "pp vs a year ago",
                items=items, source=abs_src(flow, key))


def states() -> list[dict]:
    return [
        _by_state("LF", f"M13.3.1599.20.{STATE_CODES}.M", "unemployment_by_state", "Unemployment rate by state",
                  "%", "jobs", 12, change="pp"),
        _by_state("ERP_COMP_Q", f"10.{STATE_CODES}.Q", "population_by_state", "Population by state", "people",
                  "population", 4, to_mult=0, nd=0),
        _by_state("RES_DWELL_ST", f"5.{STATE_CODES}.Q", "dwelling_price_by_state", "Mean dwelling price by state",
                  "$'000", "housing", 4, to_mult=3),
    ]


def job_ads_by_occupation() -> dict:
    d = jsa.ivi()
    f = d["frame"]
    months = [c for c in f.columns if c[:2] == "20"]
    cur, ago = months[-1], months[-13]
    sub = f[f["level"] == 3]
    items = [dict(key=r["code"], label=r["title"], value=round(float(r[cur])),
                  change_pct=round((r[cur] / r[ago] - 1) * 100, 1) if r[ago] else None)
             for _, r in sub.iterrows()]
    items.sort(key=lambda x: -x["value"])
    return dict(id="job_ads_by_occupation", title="Where the job ads are (by occupation)", unit="ads per month",
                section="jobs", as_of=cur, change_unit="% vs a year ago", items=items,
                source={"name": JSA, "dataset": "Internet Vacancy Index, ANZSCO sub-major groups (trend)",
                        "url": d["url"]},
                notes="Online job ads on SEEK, CareerOne and Workforce Australia, sorted by number of ads. "
                      "Growth rates for small groups (under ~1,000 ads) are noisy.")

