# aus-economy

A plain-English dashboard of the Australian economy: how the country makes money, how it spends it, how things are going, and what it means for everyday decisions. All data comes from official sources (ABS, RBA, Treasury/Finance).

## Status

Live dashboard with daily data refresh. Live at https://umairzeb.github.io/aus-economy/

## Daily refresh and hosting

`.github/workflows/refresh-and-deploy.yml` runs every day at 6:30am AEST (7:30am AEDT):

1. runs the pipeline and commits any new data to `main`
2. builds the site and publishes it to GitHub Pages
3. if a source is down, its last good data stays on the site and the run carries on; the run is only marked failed (GitHub emails you) if a source has been down for over 14 days or a number looks wrong

It also redeploys on every push to `main`, and can be run by hand from the repo's Actions tab ("Run workflow"). Tick "check only" to test the data sources on any branch without committing or deploying.

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
- `src/TopBar.tsx`: sticky section links and chart range
- `src/range.tsx`: the page-wide 5y / 10y / 30y / All switch
- `src/events.ts`: major events marked on time charts
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

A failed source never blocks the others: its last good files stay in place and are listed under `stale` in the manifest. The build exits non-zero only if a value falls outside its sanity range, a source has been stale for over 14 days, or a failed source has no earlier data.

Code layout:

- `pipeline/sources/`: one module per publisher (`abs`, `rba`, `budget`)
- `pipeline/registry.py`: directly-sourced series (add a series here)
- `pipeline/derived.py`: computed series (growth rates, real wages, spliced CPI)
- `pipeline/bundles.py`: cross-sections
- `docs/data-sources.md`: source quirks and caveats
