# aus-economy

A plain-English dashboard of the Australian economy: how the country makes money, how it spends it, how things are going, and what it means for everyday decisions. All data comes from official sources (ABS, RBA, Treasury/Finance, Jobs and Skills Australia).

## Status

Step 1 (data pipeline) and step 2 (glance page) done. Next: deep-dive pages.

## Website

React + Vite + TypeScript, charts with Apache ECharts. It reads the JSON in `public/data`.

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # static site in dist/
```

- `src/App.tsx`: page layout, summary and stat tiles
- `src/sections.tsx`: the four question sections
- `src/insights.ts`: rules that turn numbers into plain-English readings (descriptive only, never advice)
- `src/charts.ts`, `src/cards.tsx`: chart builders and chart cards (each card has a table view)
- `src/styles.css`: colour tokens for light and dark mode

## Data pipeline

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python
.venv/Scripts/python -m pipeline.build
```

Writes:

- `public/data/series/<id>.json`: one time series: `points` as `[iso_date, value]`, plus `title`, `unit`, `freq`, `source`, `notes`, optional `target_band`, `breaks` and `forecast_from`
- `public/data/bundles/<id>.json`: cross-sections for bar charts (exports by country, budget mix, state comparisons)
- `public/data/manifest.json`: every series' latest, previous and year-ago values, plus run errors and sanity warnings

The build exits non-zero if any source fails or a value falls outside its sanity range. A failed source never blocks the others.

Code layout:

- `pipeline/sources/`: one module per publisher (`abs`, `rba`, `budget`, `jsa`)
- `pipeline/registry.py`: directly-sourced series (add a series here)
- `pipeline/derived.py`: computed series (growth rates, real wages, spliced CPI)
- `pipeline/bundles.py`: cross-sections
- `docs/data-sources.md`: source quirks and caveats
