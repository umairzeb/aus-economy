// One plain-English line per chapter, worked out from the data. Descriptive only, never advice.
import { actuals, last, yearAgo, type Data } from "./data";
import { fmt, pct, periodLabel } from "./format";

const today = () => new Date().toISOString().slice(0, 10);
const verb = (v: number) => (v >= 0 ? "grew" : "shrank");

/** ", up from 3.60% a year ago" */
function sinceYearAgo(now: number, ago: number | undefined, dp: number): string {
  if (ago === undefined) return "";
  return Math.abs(now - ago) < 0.5 * 10 ** -dp ? ", unchanged on a year ago" : `, ${now > ago ? "up" : "down"} from ${pct(ago, dp)} a year ago`;
}

export function costVerdict(d: Data): string | undefined {
  const { cpi_yoy: cpi, wpi_yoy: wpi } = d.series;
  if (!cpi || !wpi) return undefined;
  const prices = last(cpi)[1];
  const wages = last(wpi)[1];
  return `Prices rose ${pct(prices)} in the year to ${periodLabel(last(cpi)[0])} and wages ${pct(wages)} in the year to ${periodLabel(last(wpi)[0], "Q")}, so pay ${prices > wages ? "buys less" : "goes further"}.`;
}

export function jobsVerdict(d: Data): string | undefined {
  const { unemployment_rate: ur, underemployment_rate: under } = d.series;
  if (!ur) return undefined;
  const now = last(ur)[1];
  return `${pct(now)} of the labour force is unemployed${sinceYearAgo(now, yearAgo(ur), 1)}${under ? `, and a further ${pct(last(under)[1])} want more hours` : ""}.`;
}

export function ratesVerdict(d: Data): string | undefined {
  const { cash_rate: cash, mortgage_rate_discounted: mr } = d.series;
  if (!cash) return undefined;
  const now = last(cash)[1];
  return `The RBA cash rate is ${pct(now, 2)}${sinceYearAgo(now, yearAgo(cash, today()), 2)}${mr ? `; a typical new variable mortgage costs ${pct(last(mr)[1], 2)}` : ""}.`;
}

export function housingVerdict(d: Data): string | undefined {
  const hp = d.series.dwelling_mean_price;
  if (!hp || hp.points.length < 2) return undefined;
  const [date, v] = last(hp);
  const q = (v / hp.points.at(-2)![1] - 1) * 100;
  const ago = yearAgo(hp);
  const y = ago ? (v / ago - 1) * 100 : undefined;
  const move = (x: number) => `${x < 0 ? "down" : "up"} ${pct(Math.abs(x))}`;
  return `The average home is worth $${fmt(v / 1000, 2)}m (${periodLabel(date, "Q")}): ${move(q)} on the quarter${y === undefined ? "" : ` and ${move(y)} on a year earlier`}. Official data runs months behind.`;
}

export function economyVerdict(d: Data): string | undefined {
  const { gdp_growth_yoy: gdp, gdp_per_capita_growth_yoy: gpc } = d.series;
  if (!gdp) return undefined;
  const g = last(gdp)[1];
  let s = `The economy ${verb(g)} ${pct(Math.abs(g))} in the year to ${periodLabel(last(gdp)[0], "Q")}`;
  if (gpc) {
    const p = last(gpc)[1];
    s += `. Per person it ${verb(p)} ${pct(Math.abs(p))}${g > 0 && p < g / 2 ? ", so most of the growth comes from a bigger population" : ""}`;
  }
  return `${s}.`;
}

export function budgetVerdict(d: Data): string | undefined {
  const { budget_balance: bal, budget_balance_pct_gdp: balPct, net_debt_pct_gdp: debt } = d.series;
  if (!bal) return undefined;
  const [date, v] = actuals(bal).at(-1)!;
  const share = balPct ? actuals(balPct).at(-1) : undefined;
  return `The ${periodLabel(date, "FY")} ${v < 0 ? "deficit" : "surplus"} was $${fmt(Math.abs(v) / 1000, 1)}bn${share ? ` (${pct(Math.abs(share[1]))} of GDP)` : ""}${debt ? `, and net debt is ${pct(actuals(debt).at(-1)![1])} of GDP` : ""}.`;
}

export function businessVerdict(d: Data): string | undefined {
  const { business_rate_small: small, business_rate_large: large, insolvencies_12m: ins } = d.series;
  const parts: string[] = [];
  if (small && large) {
    const diff = last(small)[1] - last(large)[1];
    parts.push(`Small businesses pay ${fmt(Math.abs(diff), 1)} points ${diff >= 0 ? "more" : "less"} than large ones to borrow`);
  }
  if (ins) parts.push(`${fmt(last(ins)[1], 0)} companies entered administration in the 12 months to ${periodLabel(last(ins)[0])}`);
  return parts.length ? `${parts.join(", and ")}.` : undefined;
}
