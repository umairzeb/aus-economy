# Data sources

Findings from the step 1 data check (26 Oct 2026). Every source below is free, needs no API key, and is fetched automatically by `python -m pipeline.build`.

| Source | Access | Update cadence | Used for |
|---|---|---|---|
| ABS Data API (`data.api.abs.gov.au`) | SDMX REST, CSV output | Monthly / quarterly per release | CPI, jobs, wages, GDP, trade, housing, population, spending |
| RBA statistical tables (`rba.gov.au/statistics/tables/csv/`) | CSV files | Daily to quarterly | Cash rate, mortgage rates, bond yields, AUD, household debt |
| Budget Paper No. 1 tables (data.gov.au, Dept of Finance) | ZIP of CSVs via CKAN API | Yearly (May Budget) | Revenue by tax, spending by function, deficit and debt history |
| ABS data cubes (abs.gov.au) | Excel, link found on the "latest-release" page | Yearly | Businesses opening and closing by size (Counts of Australian Businesses, 8165.0 Table 13) |
| ASIC insolvency statistics | Excel, link found on the statistics page | Monthly | Companies entering administration (Series 1) |
| Indeed Hiring Lab job postings tracker (GitHub, CC BY 4.0) | CSV | Daily | Job-ad trends, overall and by job type. Not an official statistic |

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
- `bond_10y`, `aud_usd` and `aud_twi` splice frozen RBA history workbooks (`xls-hist/f02histhist.xls`, `xls-hist/f11hist-1969-2009.xls`, read with the calamine engine) in front of the current CSVs, giving monthly data from 1969-70. The joins line up without jumps.

## Budget

- Dataset name pattern: `budget-YYYY-YYYY-and-portfolio-budget-statements-pbs-tables-and-data`. The pipeline tries the current year first and falls back to earlier years.
- Key tables: 5.7 (receipts by tax head), 6.3 (expenses by function), 11.1 (receipts, payments, balance since 1970-71), 11.4 (net debt and interest).
- Rows marked `(e)` are Treasury estimates. Series carry `forecast_from`, and the manifest headline uses the last actual year.
- MYEFO (December) updates are a separate publication and not yet wired in.

## Job vacancies (replaced Jobs and Skills Australia)

- The "Where the jobs are" chart uses ABS Job Vacancies by industry (`JV`, original series, compared with the same quarter a year earlier). It is quarterly; the survey month is February, May, August or November.
- It used to use the Jobs and Skills Australia Internet Vacancy Index (online job ads by occupation, monthly). jobsandskills.gov.au stalls requests from cloud servers such as GitHub Actions, even with retries and normal browser headers, while the same files download instantly from a home connection. The daily refresh failed every day, so the source was dropped (Oct 2026). Bringing it back would need the data fetched from a home connection.

## Business

- RBA F7 has interest rates on new and outstanding business loans by size (small, medium, large), monthly from July 2019. The older F5 small/large business indicator rates are mostly discontinued.
- ABS `LEND_BUSINESS` splits new loan commitments by size for small and medium businesses only (quarterly, original). Large-business and total figures aren't published by size, so the dashboard shows rolling 12-month totals for small and medium.
- Counts of Australian Businesses is not in the Data API. The pipeline finds `8165DC01.xlsx` on the latest-release page and reads Table 13 (employment size ranges: operating, entries, exits, entry and exit rates by financial year).
- ASIC's Series 1 workbook is about 17 MB. Table "1" lays months down the rows and financial years across the columns; the pipeline turns it into a monthly series and a rolling 12-month total.
- Indeed's index is 1 Feb 2020 = 100. The overall series is seasonally adjusted and kept weekly; the by-category file is not seasonally adjusted, so it is compared with the same date a year earlier.

## Not yet covered (candidates for later steps)

- RBA forecasts (Statement on Monetary Policy): published as HTML tables, not CSV.
- MYEFO and Final Budget Outcome updates.
- US comparison series (FRED CSV downloads need no key).
- ABS release calendar for the "what changed this month" feed.
- Rents beyond CPI (e.g. new-lease rents) and an income measure for mortgage-affordability calculations.

## Licensing (check before public launch)

ABS, data.gov.au budget data and Indeed Hiring Lab data are CC BY 4.0 and need attribution. ASIC statistics are reusable with attribution. RBA content is reusable with attribution under their copyright pages. Confirm the exact terms and attribution wording before the site goes public.
