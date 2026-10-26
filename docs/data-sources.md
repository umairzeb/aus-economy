# Data sources

Findings from the step 1 data check (26 Oct 2026). Every source below is free, needs no API key, and is fetched automatically by `python -m pipeline.build`.

| Source | Access | Update cadence | Used for |
|---|---|---|---|
| ABS Data API (`data.api.abs.gov.au`) | SDMX REST, CSV output | Monthly / quarterly per release | CPI, jobs, wages, GDP, trade, housing, population, spending |
| RBA statistical tables (`rba.gov.au/statistics/tables/csv/`) | CSV files | Daily to quarterly | Cash rate, mortgage rates, bond yields, AUD, household debt |
| Budget Paper No. 1 tables (data.gov.au, Dept of Finance) | ZIP of CSVs via CKAN API | Yearly (May Budget) | Revenue by tax, spending by function, deficit and debt history |
| Jobs and Skills Australia, Internet Vacancy Index | XLSX, URL changes monthly (scraped from page) | Monthly | Online job ads by occupation |

## ABS

- Query format: `https://data.api.abs.gov.au/rest/data/ABS,{FLOW}/{KEY}?format=csv&startPeriod=YYYY-MM`. The key is dot-separated dimension codes in the dataflow's order; an empty slot is a wildcard and `+` joins codes.
- An empty result comes back as HTTP 404 or a `NoRecordsFound` body. The pipeline treats both as "no data".
- `UNIT_MULT` is not always right: some national accounts flows report $m values with multiplier 0. The `SANITY` ranges in `pipeline/build.py` catch magnitude mistakes.
- **CPI changed in late 2025.** The ABS replaced the quarterly CPI and the Monthly CPI Indicator with a complete monthly CPI (dataflow `CPI`, v2.0.0). Its annual-change series only starts Apr 2025.
  - `cpi_yoy` / `trimmed_mean_yoy` splice the old indicator (`CPI_M`, from Sep 2018) onto the new CPI. Trimmed mean steps up ~0.5pp at the join because the two measures differ. The series carries a `breaks` marker so charts can annotate it.
  - Long history uses the quarterly index (back to 1948) and `CPI_Q` trimmed mean (from 1983).
- Housing lending: owner-occupier and investor loans use loan purpose `TOTDWELL`; first home buyer loans use `TOTHOUS`. Other combinations return nothing.
- Building approvals in `BA_GCCSA` are original (unadjusted) only, so the dashboard uses rolling 12-month totals.
- Imports and services debits are negative in ABS data; the registry flips them (`negate=True`).
- GDP by industry (`ANA_IND_GVA`) is chain volume only, so industry shares are approximate.

## RBA

- Each CSV has ~10 metadata rows ending in `Series ID`, then one row per date.
- Tables carry empty placeholder rows past the latest date (e.g. E2 and H1 run to 2027), and some columns are discontinued (OIS ended Nov 2022). Always take the last non-empty value per series.
- Send a browser-like User-Agent.
- `bond_10y` (F2.1) starts in 2013. Longer history is in RBA's historical workbooks if needed later.

## Budget

- Dataset name pattern: `budget-YYYY-YYYY-and-portfolio-budget-statements-pbs-tables-and-data`. The pipeline tries the current year first and falls back to earlier years.
- Key tables: 5.7 (receipts by tax head), 6.3 (expenses by function), 11.1 (receipts, payments, balance since 1970-71), 11.4 (net debt and interest).
- Rows marked `(e)` are Treasury estimates. Series carry `forecast_from`, and the manifest headline uses the last actual year.
- MYEFO (December) updates are a separate publication and not yet wired in.

## Jobs and Skills Australia

- Page: <https://www.jobsandskills.gov.au/data/internet-vacancy-index>. The pipeline finds the `anzsco2_occupations_states_and_territories` workbook link and reads the `Trend` sheet.
- Level 1 = total, level 2 = 8 major occupation groups, level 3 = ~43 sub-major groups.

## Not yet covered (candidates for later steps)

- RBA forecasts (Statement on Monetary Policy): published as HTML tables, not CSV.
- MYEFO and Final Budget Outcome updates.
- US comparison series (FRED CSV downloads need no key).
- ABS release calendar for the "what changed this month" feed.
- Rents beyond CPI (e.g. new-lease rents) and an income measure for mortgage-affordability calculations.

## Licensing (check before public launch)

ABS and data.gov.au budget data are CC BY 4.0 and need attribution. RBA and JSA content is reusable with attribution under their copyright pages. Confirm the exact terms and attribution wording before the site goes public.
