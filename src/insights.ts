// Plain-English readings generated from the data. Rules only describe what the
// numbers show; they never recommend actions.
import { last, since, valueAt, yearAgo, type Data, type Series } from "./data";
import { compact, fmt, pct, periodLabel, signed } from "./format";
import type { TileProps, Tone } from "./components/ui";

const pts = (v: number, dp = 1) => `${signed(v, dp)} pts`;

function yoyDelta(s: Series, upIsGood: boolean | null, unit: (v: number) => string = pts): TileProps["delta"] {
  const now = last(s)[1];
  const ago = yearAgo(s);
  if (ago === undefined) return undefined;
  const d = now - ago;
  const tone = upIsGood === null || Math.abs(d) < 1e-9 ? "neutral" : (d > 0) === upIsGood ? "good" : "bad";
  return { text: unit(d), tone, vs: "vs a year ago" };
}

const spark = (s: Series, years = 5) => {
  const [d] = last(s);
  return since(s.points, `${Number(d.slice(0, 4)) - years}${d.slice(4)}`);
};

const asOf = (s: Series) => periodLabel(last(s)[0], s.freq);

export function buildTiles(data: Data): TileProps[] {
  const S = data.series;
  const tiles: TileProps[] = [];

  const cpi = S.cpi_yoy;
  if (cpi) {
    const v = last(cpi)[1];
    const [lo, hi] = cpi.target_band ?? [2, 3];
    const chip: { tone: Tone; text: string } =
      v > hi ? { tone: "serious", text: "Above the RBA's 2–3% target" }
        : v < lo ? { tone: "warning", text: "Below the RBA's 2–3% target" }
          : { tone: "good", text: "Within the RBA's 2–3% target" };
    tiles.push({ label: "Inflation", href: "#chart-inflation", value: pct(v), delta: yoyDelta(cpi, false), chip,
      read: "How much prices rose over the past year.", spark: spark(cpi), asOf: asOf(cpi) });
  }

  const ur = S.unemployment_rate;
  if (ur) {
    const v = last(ur)[1];
    const ago = yearAgo(ur) ?? v;
    const d = v - ago;
    const under = S.underemployment_rate ? last(S.underemployment_rate)[1] : undefined;
    tiles.push({ label: "Unemployment", href: "#chart-jobs", value: pct(v), delta: yoyDelta(ur, false),
      chip: d > 0.2 ? { tone: "warning", text: "Job market softening" } : d < -0.2 ? { tone: "good", text: "Job market tightening" } : { tone: "neutral", text: "Broadly steady" },
      read: under !== undefined ? `Another ${pct(under)} have a job but want more hours.` : undefined,
      spark: spark(ur), asOf: asOf(ur) });
  }

  const rw = S.real_wage_growth;
  if (rw) {
    const v = last(rw)[1];
    tiles.push({ label: "Real wage growth", href: "#chart-wages", value: signed(v, 1, "%"), delta: yoyDelta(rw, true),
      chip: v < 0 ? { tone: "serious", text: "Prices rising faster than pay" } : { tone: "good", text: "Pay rising faster than prices" },
      read: S.wpi_yoy && S.cpi_yoy_q ? `${periodLabel(last(rw)[0], "Q")}: wages ${signed(valueAt(S.wpi_yoy, last(rw)[0]) ?? 0, 1, "%")}, prices ${signed(valueAt(S.cpi_yoy_q, last(rw)[0]) ?? 0, 1, "%")}.` : undefined,
      spark: spark(rw), asOf: asOf(rw) });
  }

  const cash = S.cash_rate;
  if (cash) {
    const v = last(cash)[1];
    const ago = yearAgo(cash, new Date().toISOString().slice(0, 10)) ?? v;
    const d = v - ago;
    tiles.push({ label: "RBA cash rate", href: "#chart-borrowing", value: pct(v, 2),
      delta: { text: pts(d, 2), tone: "neutral", vs: "vs a year ago" },
      chip: d > 0 ? { tone: "warning", text: "Rates rising" } : d < 0 ? { tone: "good", text: "Rates falling" } : { tone: "neutral", text: "On hold" },
      read: "Sets the cost of borrowing across the economy.",
      spark: spark(withToday(cash), 5), asOf: `Last change ${periodLabel(last(cash)[0], "event")}` });
  }

  const gpc = S.gdp_per_capita_growth_yoy;
  if (gpc) {
    const v = last(gpc)[1];
    const g = S.gdp_growth_yoy ? last(S.gdp_growth_yoy)[1] : undefined;
    tiles.push({ label: "Growth per person", href: "#chart-growth", value: signed(v, 1, "%"), delta: yoyDelta(gpc, true),
      chip: v < 0 ? { tone: "serious", text: "Shrinking per person" } : v < 1 ? { tone: "warning", text: "Weak" } : { tone: "good", text: "Growing" },
      read: g !== undefined ? `Total economy ${signed(g, 1, "%")}; the rest is population growth.` : undefined,
      spark: spark(gpc), asOf: asOf(gpc) });
  }

  const mr = S.mortgage_rate_discounted;
  if (mr) {
    tiles.push({ label: "Mortgage rate", href: "#chart-borrowing", value: pct(last(mr)[1], 2), delta: yoyDelta(mr, false, (v) => pts(v, 2)),
      read: "Typical discounted variable rate at the big banks.", spark: spark(mr), asOf: asOf(mr) });
  }

  const pg = S.population_growth_yoy;
  if (pg) {
    const nom = S.nom_annual ? last(S.nom_annual)[1] : undefined;
    const nat = S.natural_increase_annual ? last(S.natural_increase_annual)[1] : undefined;
    const share = nom !== undefined && nat !== undefined ? Math.round((nom / (nom + nat)) * 100) : undefined;
    tiles.push({ label: "Population growth", value: pct(last(pg)[1], 1), delta: yoyDelta(pg, null),
      read: nom !== undefined && share !== undefined ? `${compact(nom + (nat ?? 0))} more people a year; ${share}% from migration.` : undefined,
      spark: spark(pg), asOf: asOf(pg) });
  }

  const aud = S.aud_usd;
  if (aud) {
    const d = last(aud)[1] - (yearAgo(aud) ?? last(aud)[1]);
    tiles.push({ label: "Australian dollar", value: `US$${fmt(last(aud)[1], 2)}`,
      delta: { text: signed(d * 100, 1, "c"), tone: "neutral", vs: "vs a year ago" },
      read: d < 0 ? "Weaker: imports and overseas travel cost more." : "Stronger: imports and overseas travel cost less.",
      spark: spark(aud), asOf: asOf(aud) });
  }
  return tiles;
}

/** Extend an event series (one point per decision) to today so step lines reach the present. */
export function withToday(s: Series): Series {
  const today = new Date().toISOString().slice(0, 10);
  const [d, v] = last(s);
  return d >= today ? s : { ...s, points: [...s.points, [today, v]] };
}

export function buildSummary(data: Data): string[] {
  const S = data.series;
  const out: string[] = [];

  if (S.cpi_yoy) {
    const v = last(S.cpi_yoy)[1];
    let s = v > 3 ? `Prices are rising faster than the Reserve Bank wants: ${pct(v)} over the past year, against a 2–3% target`
      : v < 2 ? `Inflation is low at ${pct(v)}, below the Reserve Bank's 2–3% target`
        : `Inflation is within the Reserve Bank's 2–3% target at ${pct(v)}`;
    if (S.real_wage_growth) {
      const rw = last(S.real_wage_growth)[1];
      s += rw < 0 ? ", and faster than wages, so the average pay packet buys less than a year ago."
        : ", but wages are rising faster, so pay is going further than a year ago.";
    } else s += ".";
    out.push(s);
  }

  if (S.cash_rate) {
    const v = last(S.cash_rate)[1];
    const d = v - (yearAgo(S.cash_rate, new Date().toISOString().slice(0, 10)) ?? v);
    out.push(d > 0 ? `To slow inflation, the RBA has raised the cash rate to ${pct(v, 2)}, ${fmt(d, 2)} points higher than a year ago.`
      : d < 0 ? `The RBA has cut the cash rate to ${pct(v, 2)}, ${fmt(-d, 2)} points lower than a year ago.`
        : `The RBA has held the cash rate at ${pct(v, 2)} over the past year.`);
  }

  if (S.unemployment_rate) {
    const v = last(S.unemployment_rate)[1];
    const d = v - (yearAgo(S.unemployment_rate) ?? v);
    const under = S.underemployment_rate ? ` A further ${pct(last(S.underemployment_rate)[1])} of workers have a job but want more hours.` : "";
    out.push((d > 0.2 ? `Unemployment has risen to ${pct(v)}, up from ${pct(v - d)} a year ago.`
      : d < -0.2 ? `Unemployment has fallen to ${pct(v)}, from ${pct(v - d)} a year ago.`
        : `Unemployment is steady at ${pct(v)}.`) + under);
  }

  if (S.gdp_per_capita_growth_yoy && S.gdp_growth_yoy) {
    const g = last(S.gdp_growth_yoy)[1];
    const pc = last(S.gdp_per_capita_growth_yoy)[1];
    out.push(pc < 0 ? `The economy grew ${pct(g)} over the year but shrank ${pct(-pc)} per person, so growth is coming entirely from a bigger population.`
      : pc < 1 ? `The economy grew ${pct(g)} over the year, but only ${pct(pc)} per person: most of the growth comes from a bigger population.`
        : `The economy grew ${pct(g)} over the year, or ${pct(pc)} per person.`);
  }
  return out;
}
