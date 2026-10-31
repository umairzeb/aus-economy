"""Series and bundles for the "For business" section: lending to businesses by size,
businesses opening and closing by size, company insolvencies and job postings."""
from __future__ import annotations

from . import transforms as t
from .derived import ABS, abs_src
from .sources import abs_files, asic, indeed

ASIC = "Australian Securities & Investments Commission"
INDEED = "Indeed Hiring Lab"


def series() -> list[dict]:
    """Series fetched from file-based sources (ASIC, Indeed)."""
    a = asic.companies_entering_administration()
    asic_src = {"name": ASIC, "dataset": "Insolvency statistics, Series 1", "url": a["url"]}
    return [
        dict(id="insolvencies_m", title="Companies entering administration (month)", unit="companies",
             section="business", freq="M", points=a["points"], source=asic_src, hidden=True),
        dict(id="insolvencies_12m", title="Companies entering administration (12 months)", unit="companies",
             section="business", freq="M", points=t.rolling_sum(a["points"], 12), source=asic_src,
             notes="Companies entering external administration or having a controller appointed for the first time."),
        dict(id="job_postings_indeed", title="Job ads on Indeed", unit="index (Feb 2020 = 100)", section="business",
             freq="W", points=indeed.total_postings(),
             source={"name": INDEED, "dataset": "Job postings tracker (Australia, seasonally adjusted)", "url": indeed.REPO},
             notes="Not an official statistic: counts job ads on one private job site. CC BY 4.0."),
    ]


def from_others(got) -> list[dict]:
    """Rolling 12-month business lending from the quarterly ABS series."""
    out = []
    for size in ("small", "medium"):
        q = got(f"lending_{size}_business_q")
        if q:
            out.append(dict(id=f"lending_{size}_business_12m", title=f"New loans to {size} businesses (12 months)",
                            unit="$bn", section="business", freq="Q",
                            points=t.scale(t.rolling_sum(q, 4), 1 / 1000, 1),
                            source=abs_src("LEND_BUSINESS", "FIN_VAL.NEWCOMMITS.DV8270.TOTLOANPURP_EXCLREFIN.TOT.DV8605+DV8604.10.AUS.Q"),
                            notes="Fixed-term loans, excluding refinancing. The ABS doesn't publish this split for large businesses."))
    return out


def business_counts_by_size() -> dict:
    d = abs_files.business_counts_by_size()
    latest = max(r["year"] for r in d["rows"])
    items = [dict(key=r["band"], label=r["band"], value=r["operating_end"], change_pct=r["change_pct"],
                  entry_rate=r["entry_rate"], exit_rate=r["exit_rate"], entries=r["entries"], exits=r["exits"])
             for r in d["rows"] if r["year"] == latest]
    return dict(id="business_counts_by_size", title="Businesses opening and closing, by size", unit="businesses",
                section="business", as_of=latest, items=items, history=d["rows"],
                source={"name": ABS, "dataset": "Counts of Australian Businesses (8165.0), Table 13", "url": d["url"]},
                notes="Entry rate = businesses that started during the year as a share of those operating at the "
                      "start; exit rate = those that stopped. Size is number of employees.")


def job_postings_by_category() -> dict:
    d = indeed.by_category()
    return dict(id="job_postings_by_category", title="Job ads on Indeed, by type of job", unit="index (Feb 2020 = 100)",
                section="business", as_of=d["as_of"], change_unit="% vs a year ago", items=d["items"],
                source={"name": INDEED, "dataset": "Job postings tracker, by category (Australia)", "url": indeed.REPO},
                notes="Not an official statistic: counts job ads on one private job site. CC BY 4.0.")
