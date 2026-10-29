"""Fetch every source and write data/series/*.json, data/bundles/*.json and
data/manifest.json. Run with:  python -m pipeline.build

One failing source never stops the run: its error is recorded in the
manifest and the previous JSON file (if any) is left in place. The exit code
is non-zero only for sanity warnings, data stale for over STALE_DAYS, or a
failed source with nothing to fall back on.
"""
from __future__ import annotations

import json
import sys
import time
import traceback
from datetime import datetime, timezone

from . import bundles, derived
from .registry import ABS_FLOWS, RBA_TABLES, SERIES
from .sources import abs as abs_
from .sources import rba
from .transforms import splice, value_at_or_before
from .util import DATA_DIR, now_iso, write_json

# A source may keep serving its last good data for this long before the run fails.
STALE_DAYS = 14

# Plausible range for each headline's latest value. Catches unit/multiplier
# mistakes and upstream format changes before they reach the dashboard.
SANITY = {
    "unemployment_rate": (1, 15), "underemployment_rate": (2, 20), "participation_rate": (55, 75),
    "cpi_yoy": (-3, 15), "trimmed_mean_yoy": (-2, 12), "wpi_yoy": (0, 10), "cash_rate": (0, 15),
    "gdp_real": (4e5, 1.5e6), "gdp_per_capita_real": (15000, 40000), "population": (2.5e7, 3.3e7),
    "exports_goods": (2e4, 1e5), "imports_goods": (2e4, 1e5), "dwelling_mean_price": (500, 2000),
    "mortgage_rate_variable": (3, 15), "aud_usd": (0.4, 1.2), "bond_10y": (0, 10),
    "household_debt_to_income": (100, 250), "job_vacancies": (100, 600), "job_ads_total": (5e4, 4e5),
    "dwelling_approvals_12m": (1e5, 3e5), "nom_annual": (-1e5, 7e5),
}


def source_for(spec: dict) -> dict:
    if "abs" in spec:
        flow, key = spec["abs"]
        return {"name": derived.ABS, "dataset": ABS_FLOWS.get(flow, flow), "url": f"{abs_.BASE}/ABS,{flow}/{key}"}
    table, sid = spec["rba"]
    return {"name": derived.RBA, "dataset": RBA_TABLES.get(table, table), "series_id": sid,
            "url": rba.CSV_URL.format(table=table)}


def fetch_direct(spec: dict) -> dict:
    if "abs" in spec:
        flow, key = spec["abs"]
        pts = abs_.series(flow, key, to_mult=spec.get("to_mult"))
    else:
        pts = rba.series(*spec["rba"])
        if spec.get("rba_hist"):
            pts = splice(rba.hist_table(spec["rba_hist"])[spec["rba"][1]], pts)
    if spec.get("negate"):  # ABS records imports as debits (negative)
        pts = [[d, -v] for d, v in pts]
    out = {k: v for k, v in spec.items() if k not in ("abs", "rba", "rba_hist", "to_mult", "negate")}
    return out | {"points": pts, "source": source_for(spec)}


def summarise(s: dict) -> dict:
    pts = s["points"]
    extra = {}
    if s.get("forecast_from"):  # budget series: headline is the last actual, not a forecast
        forecasts = [p for p in pts if p[0] >= s["forecast_from"]]
        pts = [p for p in pts if p[0] < s["forecast_from"]]
        extra["forecasts"] = forecasts
    d, v = pts[-1]
    year_ago_date = f"{int(d[:4]) - 1}{d[4:]}"
    ya = value_at_or_before(pts, year_ago_date)
    return {
        "latest": {"date": d, "value": v},
        "previous": {"date": pts[-2][0], "value": pts[-2][1]} if len(pts) > 1 else None,
        "year_ago": {"date": year_ago_date, "value": ya} if ya is not None else None,
        "first_date": pts[0][0], "count": len(s["points"]),
    } | extra


def main() -> int:
    t0 = time.time()
    built: dict[str, dict] = {}
    manifest = {"generated": now_iso(), "series": [], "bundles": [], "errors": []}

    def record_error(what: str, e: Exception):
        manifest["errors"].append({"id": what, "error": f"{type(e).__name__}: {e}"})
        print(f"  FAIL {what}: {type(e).__name__}: {e}", file=sys.stderr)
        if "-v" in sys.argv:
            traceback.print_exc()

    def keep(s: dict):
        if not s.get("points"):
            raise ValueError(f"{s['id']}: no data points")
        built[s["id"]] = s

    print("Direct series")
    for spec in SERIES:
        try:
            keep(fetch_direct(spec))
        except Exception as e:  # noqa: BLE001
            record_error(spec["id"], e)

    print("Derived series")
    for builder in (derived.cpi_monthly, derived.cpi_quarterly, derived.cpi_components,
                    derived.budget_history, derived.job_ads):
        try:
            for s in builder():
                keep(s)
        except Exception as e:  # noqa: BLE001
            record_error(builder.__name__, e)

    def got(sid: str) -> list[list]:
        if sid not in built:
            raise KeyError(f"depends on missing series {sid}")
        return built[sid]["points"]

    try:
        others = derived.from_others(lambda sid: got(sid) if sid in built else [])
        for s in others:
            if s["points"]:
                keep(s)
            else:
                record_error(s["id"], ValueError("inputs missing"))
    except Exception as e:  # noqa: BLE001
        record_error("from_others", e)

    print("Bundles")
    bundle_list = []
    for builder in (bundles.exports_by_country, bundles.exports_by_commodity, bundles.gdp_by_industry,
                    bundles.revenue_mix, bundles.spending_by_function, bundles.job_ads_by_occupation,
                    lambda: bundles.cpi_breakdown(lambda sid: built.get(sid, {}).get("points")),
                    bundles.states):
        try:
            res = builder()
            bundle_list += res if isinstance(res, list) else [res]
        except Exception as e:  # noqa: BLE001
            record_error(getattr(builder, "__name__", "bundle"), e)

    warnings = []
    for sid, s in built.items():
        info = summarise(s)
        lo_hi = SANITY.get(sid)
        if lo_hi and not lo_hi[0] <= info["latest"]["value"] <= lo_hi[1]:
            warnings.append(f"{sid}: latest {info['latest']['value']} outside {lo_hi}")
        write_json(DATA_DIR / "series" / f"{sid}.json", s | {"updated": manifest["generated"]})
        manifest["series"].append({k: s.get(k) for k in ("id", "title", "section", "unit", "freq", "hidden")}
                                  | {"source": s["source"]["name"]} | info)

    for b in bundle_list:
        write_json(DATA_DIR / "bundles" / f"{b['id']}.json", b | {"updated": manifest["generated"]})
        manifest["bundles"].append({k: b.get(k) for k in ("id", "title", "section", "unit", "as_of")}
                                   | {"items": len(b["items"])})

    # Files this run didn't rewrite keep their last good data. That's fine for a
    # short outage, but a source stale for longer than STALE_DAYS fails the run.
    written = {f"series/{sid}.json" for sid in built} | {f"bundles/{b['id']}.json" for b in bundle_list}
    stale, too_stale = [], []
    for f in sorted(DATA_DIR.glob("*/*.json")):
        rel = f.relative_to(DATA_DIR).as_posix()
        if rel in written:
            continue
        updated = json.loads(f.read_text(encoding="utf-8")).get("updated")
        age = (datetime.now(timezone.utc) - datetime.fromisoformat(updated)).days if updated else None
        stale.append({"file": rel, "updated": updated, "age_days": age})
        if age is None or age > STALE_DAYS:
            too_stale.append(rel)

    manifest["warnings"] = warnings
    manifest["stale"] = stale
    write_json(DATA_DIR / "manifest.json", manifest)

    print(f"\n{len(built)} series, {len(bundle_list)} bundles, {len(manifest['errors'])} source errors, "
          f"{len(stale)} stale files, {len(warnings)} warnings in {time.time() - t0:.0f}s")
    for w in warnings:
        print("  WARN", w)
    if stale:
        oldest = max(x["age_days"] or 0 for x in stale)
        print(f"  STALE {len(stale)} files kept from earlier runs (oldest {oldest} days)")
    # A failed source with no earlier data to fall back on also fails the run.
    unreplaced = bool(manifest["errors"]) and not stale
    return 1 if warnings or too_stale or unreplaced else 0


if __name__ == "__main__":
    sys.exit(main())
