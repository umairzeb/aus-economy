# aus-economy

A plain-English dashboard of the Australian economy: how the country makes money, how it spends it, how things are going, and what it means for everyday decisions. All data comes from official sources (ABS, RBA, Treasury/Finance, Jobs and Skills Australia).

## Status

Step 1 (data pipeline) done. Next: the glance page front-end.

## Data pipeline

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pipeline.build
```

Writes:

- `data/series/<id>.json`: one time series: `points` as `[iso_date, value]`, plus `title`, `unit`, `freq`, `source`, `notes`, optional `target_band`, `breaks` and `forecast_from`
- `data/bundles/<id>.json`: cross-sections for bar charts (exports by country, budget mix, state comparisons)
- `data/manifest.json`: every series' latest, previous and year-ago values, plus run errors and sanity warnings

The build exits non-zero if any source fails or a value falls outside its sanity range. A failed source never blocks the others.

Code layout:

- `pipeline/sources/`: one module per publisher (`abs`, `rba`, `budget`, `jsa`)
- `pipeline/registry.py`: directly-sourced series (add a series here)
- `pipeline/derived.py`: computed series (growth rates, real wages, spliced CPI)
- `pipeline/bundles.py`: cross-sections
- `docs/data-sources.md`: source quirks and caveats
