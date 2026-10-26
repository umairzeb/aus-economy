import { useEffect, useState } from "react";
import { loadData, type Data } from "./data";
import { buildSummary, buildTiles } from "./insights";
import { BudgetSection, EarnSection, GoingSection, YouSection } from "./sections";
import { StatTile } from "./components/ui";
import { TokensContext, useThemeState, type ThemePref } from "./theme";

const SERIES = [
  "cpi_yoy", "trimmed_mean_yoy", "cpi_yoy_q", "unemployment_rate", "underemployment_rate", "wpi_yoy",
  "real_wage_growth", "gdp_growth_yoy", "gdp_per_capita_growth_yoy", "cash_rate", "mortgage_rate_discounted",
  "population_growth_yoy", "nom_annual", "natural_increase_annual", "aud_usd", "trade_balance_12m",
  "exports_education_4q", "terms_of_trade", "budget_balance_pct_gdp", "net_debt_pct_gdp",
];
const BUNDLES = [
  "exports_by_commodity", "exports_by_country", "gdp_by_industry", "revenue_mix", "spending_by_function",
  "cpi_breakdown", "dwelling_price_by_state", "job_ads_by_occupation",
];

const NEXT_THEME: Record<ThemePref, ThemePref> = { auto: "light", light: "dark", dark: "auto" };
const THEME_LABEL: Record<ThemePref, string> = { auto: "Theme: auto", light: "Theme: light", dark: "Theme: dark" };

export default function App() {
  const { pref, setPref, tokens } = useThemeState();
  const [data, setData] = useState<Data | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadData(SERIES, BUNDLES).then(setData, (e: Error) => setError(e.message));
  }, []);

  // Sections render only once data arrives, so honour a #section link after that.
  useEffect(() => {
    if (data && location.hash) document.getElementById(location.hash.slice(1))?.scrollIntoView();
  }, [data]);

  const updated = data
    ? new Date(data.manifest.generated).toLocaleDateString("en-AU", { day: "numeric", month: "long", year: "numeric" })
    : null;

  return (
    <TokensContext.Provider value={tokens}>
      <div className="page">
        <header className="site-header">
          <div>
            <h1>Australia's economy, in plain English</h1>
            <p className="tagline">How the country makes and spends money, how things are going, and what it means for you. Built from official ABS, RBA, Budget and Jobs and Skills Australia data.</p>
          </div>
          <button type="button" className="theme-toggle" onClick={() => setPref(NEXT_THEME[pref])}>{THEME_LABEL[pref]}</button>
        </header>

        {error && <p className="status-msg">Couldn't load the data ({error}). Run the pipeline: python -m pipeline.build</p>}
        {!data && !error && <p className="status-msg">Loading the latest numbers…</p>}

        {data && (
          <main>
            <section className="summary" aria-label="Summary">
              <h2>In short</h2>
              <p>{buildSummary(data).join(" ")}</p>
              <div className="meta">Data updated {updated}. Each figure is the latest official release.</div>
            </section>

            <nav className="section-nav" aria-label="Sections">
              <a href="#going">How are things going?</a>
              <a href="#earn">How Australia makes money</a>
              <a href="#budget">Government money</a>
              <a href="#you">What it means for me</a>
            </nav>

            <div className="tiles">
              {buildTiles(data).map((tile) => <StatTile key={tile.label} {...tile} />)}
            </div>

            <GoingSection data={data} />
            <EarnSection data={data} />
            <BudgetSection data={data} />
            <YouSection data={data} />
          </main>
        )}

        <footer className="site-footer">
          <p>Sources: Australian Bureau of Statistics, Reserve Bank of Australia, Australian Government Budget Paper No. 1 (data.gov.au), and Jobs and Skills Australia. ABS and Budget data are used under CC BY 4.0.</p>
          <p>This site describes official statistics. It is not financial advice.</p>
        </footer>
      </div>
    </TokensContext.Provider>
  );
}
