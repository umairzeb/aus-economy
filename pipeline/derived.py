"""Series computed from other series or from multi-series ABS queries.

Each builder takes `got(id)` (returns an already-built series' points) and
returns a dict with at least id/title/unit/section/freq/points/source.
"""
from __future__ import annotations

from . import transforms as t
from .registry import CPI_COMPONENTS
from .sources import abs as abs_
from .sources import budget, jsa

ABS = "Australian Bureau of Statistics"
RBA = "Reserve Bank of Australia"
BUDGET = "Australian Government Budget (Budget Paper No. 1)"
JSA = "Jobs and Skills Australia"


def abs_src(flow: str, key: str) -> dict:
    return {"name": ABS, "dataset": flow, "url": f"{abs_.BASE}/ABS,{flow}/{key}"}


def cpi_monthly() -> list[dict]:
    """Headline and trimmed mean annual inflation, monthly.

    The ABS moved to a complete monthly CPI in late 2025. Its annual-change
    history starts Apr 2025, so earlier months come from the discontinued
    Monthly CPI Indicator (from Sep 2018).
    """
    out = []
    for sid, title, old_key, new_key in [
        ("cpi_yoy", "Inflation (CPI, annual)", "3.10001.10.50.M", "3.10001.10.50.M"),
        ("trimmed_mean_yoy", "Underlying inflation (trimmed mean, annual)", "3.999905.10.50.M", "3.999902.20.50.M"),
    ]:
        old = abs_.series("CPI_M", old_key)
        new = abs_.series("CPI", new_key)
        out.append(dict(
            id=sid, title=title, unit="% y/y", section="prices", freq="M",
            points=t.splice(old, new), target_band=[2, 3],
            breaks=[{"date": new[0][0], "label": "ABS switches to full monthly CPI"}],
            source=abs_src("CPI", new_key),
            notes=f"Monthly CPI from {new[0][0][:7]}; earlier months use the Monthly CPI Indicator "
                  "(a narrower measure). RBA target band is 2-3%."))
    return out


def cpi_quarterly() -> list[dict]:
    """Long-run inflation history: quarterly CPI back to 1949."""
    idx = abs_.series("CPI", "1.10001.10.50.Q")
    tm = abs_.series("CPI_Q", "3.999902.20.50.Q")
    return [
        dict(id="cpi_yoy_q", title="Inflation (CPI, annual) - long run", unit="% y/y", section="prices", freq="Q",
             points=t.pct_change(idx, 4, 1), target_band=[2, 3], source=abs_src("CPI", "1.10001.10.50.Q"),
             notes="Computed from the quarterly all-groups CPI index."),
        dict(id="trimmed_mean_yoy_q", title="Underlying inflation (trimmed mean) - long run", unit="% y/y",
             section="prices", freq="Q", points=tm, target_band=[2, 3],
             source=abs_src("CPI_Q", "3.999902.20.50.Q")),
    ]


def cpi_components() -> list[dict]:
    codes = "+".join(c for c, _ in CPI_COMPONENTS.values())
    key = f"3.{codes}.10.50.M"
    df = abs_.fetch("CPI", key)
    out = []
    for slug, (code, label) in CPI_COMPONENTS.items():
        g = df[df["INDEX"] == code].dropna(subset=["OBS_VALUE"]).sort_values("date")
        out.append(dict(id=f"cpi_{slug}_yoy", title=f"{label} prices", label=label, unit="% y/y",
                        section="prices", freq="M", hidden=True,
                        points=[[d, float(v)] for d, v in zip(g["date"], g["OBS_VALUE"])],
                        source=abs_src("CPI", f"3.{code}.10.50.M")))
    return out


def from_others(got) -> list[dict]:
    q = lambda sid: got(sid)  # noqa: E731
    return [
        dict(id="real_wage_growth", title="Real wage growth", unit="pp", section="jobs", freq="Q",
             points=t.subtract(q("wpi_yoy"), q("cpi_yoy_q"), 1),
             source={"name": ABS, "dataset": "WPI, CPI", "url": abs_.BASE},
             notes="Wage growth minus inflation. Negative means pay is buying less than a year ago."),
        dict(id="employment_change", title="Jobs added (monthly)", unit="'000", section="jobs", freq="M",
             points=t.diff(q("employed_persons"), 1, 1),
             source={"name": ABS, "dataset": "LF", "url": abs_.BASE}),
        dict(id="gdp_growth_yoy", title="Economic growth (real GDP, annual)", unit="% y/y", section="growth",
             freq="Q", points=t.pct_change(q("gdp_real"), 4, 1),
             source={"name": ABS, "dataset": "ANA_AGG", "url": abs_.BASE}),
        dict(id="gdp_per_capita_growth_yoy", title="Growth per person (real GDP per capita, annual)",
             unit="% y/y", section="growth", freq="Q", points=t.pct_change(q("gdp_per_capita_real"), 4, 1),
             source={"name": ABS, "dataset": "ANA_AGG", "url": abs_.BASE},
             notes="If this is negative while GDP grows, the economy is only growing because there are more people."),
        dict(id="trade_balance_12m", title="Goods trade surplus (12 months)", unit="$bn", section="trade", freq="M",
             points=t.scale(t.rolling_sum(q("trade_balance_goods"), 12), 1 / 1000, 1),
             source={"name": ABS, "dataset": "ITGS", "url": abs_.BASE}),
        dict(id="exports_education_4q", title="Education exports (12 months)", unit="$bn", section="trade",
             freq="Q", points=t.scale(t.rolling_sum(q("exports_education_q"), 4), 1 / 1000, 1),
             source={"name": ABS, "dataset": "BOP", "url": abs_.BASE}),
        dict(id="dwelling_approvals_12m", title="Dwellings approved (12 months)", unit="dwellings",
             section="housing", freq="M", points=t.rolling_sum(q("dwelling_approvals_m"), 12),
             source={"name": ABS, "dataset": "BA_GCCSA", "url": abs_.BASE},
             notes="Rolling 12-month total. The National Housing Accord target is 1.2 million homes over "
                   "5 years from mid-2024 (~240,000 a year)."),
        dict(id="population_growth_yoy", title="Population growth (annual)", unit="% y/y", section="population",
             freq="Q", points=t.pct_change(q("population"), 4, 2),
             source={"name": ABS, "dataset": "ERP_COMP_Q", "url": abs_.BASE}),
        dict(id="nom_annual", title="Net overseas migration (12 months)", unit="people", section="population",
             freq="Q", points=t.rolling_sum(q("nom_q"), 4),
             source={"name": ABS, "dataset": "ERP_COMP_Q", "url": abs_.BASE}),
        dict(id="natural_increase_annual", title="Births minus deaths (12 months)", unit="people",
             section="population", freq="Q", points=t.rolling_sum(q("natural_increase_q"), 4),
             source={"name": ABS, "dataset": "ERP_COMP_Q", "url": abs_.BASE}),
    ]


def budget_history() -> list[dict]:
    b = budget.latest()
    src = {"name": BUDGET, "dataset": f"Budget {b['budget_year']}", "url": b["dataset_url"]}
    specs = [
        ("budget_receipts_pct_gdp", "Government revenue (% of GDP)", "11.1", 2, "% GDP"),
        ("budget_payments_pct_gdp", "Government spending (% of GDP)", "11.1", 5, "% GDP"),
        ("budget_balance", "Budget balance (underlying cash)", "11.1", 7, "$m"),
        ("budget_balance_pct_gdp", "Budget balance (% of GDP)", "11.1", 8, "% GDP"),
        ("net_debt_pct_gdp", "Government net debt (% of GDP)", "11.4", 2, "% GDP"),
        ("net_interest", "Net interest paid on government debt", "11.4", 3, "$m"),
    ]
    out = []
    for sid, title, table, col, unit in specs:
        pts, est = budget.history(table, col)
        out.append(dict(id=sid, title=title, unit=unit, section="budget", freq="FY", points=pts,
                        forecast_from=est, source=src,
                        notes="Financial years ending 30 June. Points from forecast_from onward are "
                              "Treasury estimates, not actuals."))
    return out


def job_ads() -> list[dict]:
    d = jsa.ivi()
    f = d["frame"]
    months = [c for c in f.columns if c[:2] == "20"]
    src = {"name": JSA, "dataset": "Internet Vacancy Index (trend)", "url": d["url"]}
    out = []
    for _, row in f[f["level"].isin([1, 2])].iterrows():
        slug = "total" if row["level"] == 1 else row["title"].lower().replace(" ", "_").replace(",", "")
        out.append(dict(id=f"job_ads_{slug}", title=f"Online job ads - {row['title'].title()}", unit="ads",
                        section="jobs", freq="M", hidden=row["level"] != 1,
                        points=[[m, round(float(row[m]))] for m in months if row[m] == row[m]],
                        source=src))
    return out
