// The four questions the dashboard answers, each a section of cards.
import type { ReactNode } from "react";
import { actuals, last, type Bundle, type Data } from "./data";
import { BarCard, ColumnCard, LineCard } from "./cards";
import type { BarItem } from "./charts";
import { withToday } from "./insights";
import { billions, fmt, pct, periodLabel, signed } from "./format";
import { useTokens } from "./theme";

function Section({ id, title, lede, children }: { id: string; title: string; lede: string; children: ReactNode }) {
  return (
    <section className="section" id={id} aria-labelledby={`${id}-h`}>
      <header>
        <h2 id={`${id}-h`}>{title}</h2>
        <p className="lede">{lede}</p>
      </header>
      {children}
    </section>
  );
}

function Mini({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="mini">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {note && <div className="note">{note}</div>}
    </div>
  );
}

/** Top n items, the rest folded into one "All other" bar. */
function topWithOther(b: Bundle, n: number, otherLabel: string) {
  const items = b.items.slice(0, n);
  const rest = b.items.slice(n);
  if (!rest.length) return items;
  const value = rest.reduce((a, i) => a + i.value, 0);
  const share = rest.reduce((a, i) => a + (i.share ?? 0), 0);
  return [...items, { key: "other", label: otherLabel, value: Math.round(value * 10) / 10, share: Math.round(share * 10) / 10 }];
}

/** Lower-case the first letter for use mid-sentence, leaving acronyms alone. */
const lc = (s: string) => s.replace(/\S+/g, (w) => (/[A-Z]{2,}/.test(w) ? w : w.toLowerCase()));

const changeText = (c: number | null | undefined, what = "on the previous 12 months") =>
  c === null || c === undefined ? "" : `${signed(c, 1, "%")} ${what}`;

// ---------------------------------------------------------------- 1

export function GoingSection({ data }: { data: Data }) {
  const t = useTokens();
  const S = data.series;
  return (
    <Section id="going" title="How are things going?"
      lede="The four numbers that shape everyday life: prices, jobs, pay and growth.">
      <div className="grid-2">
        {S.cpi_yoy && S.trimmed_mean_yoy && (
          <LineCard title="Inflation" subtitle="Annual change in consumer prices, monthly"
            takeaway={`Headline ${pct(last(S.cpi_yoy)[1])}, underlying ${pct(last(S.trimmed_mean_yoy)[1])}. The RBA aims for 2–3%.`}
            lines={[{ s: S.cpi_yoy, name: "All prices (CPI)", color: t.s1 }, { s: S.trimmed_mean_yoy, name: "Underlying (trimmed mean)", color: t.s2 }]}
            start="2018-01-01" yFormat={(v) => pct(v)} band={S.cpi_yoy.target_band} bandLabel="RBA target 2–3%" breaks />
        )}
        {S.unemployment_rate && S.underemployment_rate && (
          <LineCard title="Jobs" subtitle="Share of the labour force, seasonally adjusted"
            takeaway={`${pct(last(S.unemployment_rate)[1])} can't find work, and ${pct(last(S.underemployment_rate)[1])} have work but want more hours.`}
            lines={[{ s: S.unemployment_rate, name: "Unemployed", color: t.s1 }, { s: S.underemployment_rate, name: "Underemployed", color: t.s2 }]}
            start="2015-01-01" yFormat={(v) => pct(v)} />
        )}
        {S.wpi_yoy && S.cpi_yoy_q && (
          <LineCard title="Wages vs prices" subtitle="Annual change, quarterly"
            takeaway={last(S.wpi_yoy)[1] < last(S.cpi_yoy_q)[1]
              ? "Prices are rising faster than wages, so pay is losing buying power."
              : "Wages are rising faster than prices, so pay is gaining buying power."}
            lines={[{ s: S.wpi_yoy, name: "Wages", color: t.s1 }, { s: S.cpi_yoy_q, name: "Prices", color: t.s2 }]}
            start="2012-01-01" yFormat={(v) => pct(v)} />
        )}
        {S.gdp_growth_yoy && S.gdp_per_capita_growth_yoy && (
          <LineCard title="Economic growth" subtitle="Annual change in real GDP, quarterly"
            takeaway="When growth per person lags total growth, the economy is getting bigger mainly because there are more people."
            lines={[{ s: S.gdp_growth_yoy, name: "Whole economy", color: t.s1 }, { s: S.gdp_per_capita_growth_yoy, name: "Per person", color: t.s2 }]}
            start="2012-01-01" yFormat={(v) => pct(v)} zeroLine />
        )}
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------- 2

export function EarnSection({ data }: { data: Data }) {
  const t = useTokens();
  const { series: S, bundles: B } = data;
  const com = B.exports_by_commodity;
  const cty = B.exports_by_country;
  const ind = B.gdp_by_industry;
  const tb = S.trade_balance_12m;
  const edu = S.exports_education_4q;
  const top4 = com ? com.items.slice(0, 4).reduce((a, i) => a + (i.share ?? 0), 0) : 0;

  const exportItems = (b: Bundle, n: number): BarItem[] =>
    b.items.slice(0, n).map((i) => ({
      label: i.label, value: i.value, color: t.s1,
      extra: `${fmt(i.share ?? 0)}% of goods exports · ${changeText(i.change_pct)}`,
    }));
  const exportTable = (b: Bundle, n: number) => ({
    head: ["", "$bn (12 months)", "Share", "Change"],
    rows: b.items.slice(0, n).map((i) => [i.full_label ?? i.label, fmt(i.value), pct(i.share ?? 0), signed(i.change_pct ?? 0, 1, "%")]),
    num: [1, 2, 3],
  });

  return (
    <Section id="earn" title="How does Australia make money?"
      lede="What the economy produces, and what the rest of the world buys from us.">
      <div className="grid-3" style={{ marginBottom: 16 }}>
        {com && <Mini label="Goods exports, past 12 months" value={billions(com.total ?? 0, 0)} note={`12 months to ${periodLabel(com.as_of)}`} />}
        {tb && <Mini label="Goods trade surplus, past 12 months" value={billions(last(tb)[1])}
          note={`${billions(tb.points.find(([d]) => d >= `${Number(last(tb)[0].slice(0, 4)) - 1}${last(tb)[0].slice(4)}`)?.[1] ?? 0)} a year earlier`} />}
        {edu && <Mini label="Education exports (international students)" value={billions(last(edu)[1])}
          note={`12 months to ${periodLabel(last(edu)[0], "Q")}; Australia's largest services export`} />}
      </div>
      <div className="grid-2">
        {com && (
          <BarCard title="What we sell overseas" subtitle="Top goods exports, $bn over the past 12 months"
            takeaway={`Four products (${com.items.slice(0, 4).map((i) => lc(i.label)).join(", ").replace(/, ([^,]*)$/, " and $1")}) make up ${Math.round(top4)}% of goods exports.`}
            items={exportItems(com, 10)} valueFormat={(v) => `$${fmt(v, v < 10 ? 1 : 0)}bn`}
            sources={[com.source]} asOf={`12 months to ${periodLabel(com.as_of)}`} table={exportTable(com, 15)} />
        )}
        {cty && (
          <BarCard title="Who buys it" subtitle="Top destinations for goods exports, $bn over the past 12 months"
            takeaway={`${cty.items[0].label} buys ${fmt(cty.items[0].share ?? 0, 0)}% of our goods exports${
              (cty.items[0].share ?? 0) > cty.items.slice(1, 5).reduce((a, i) => a + (i.share ?? 0), 0) ? ", more than the next four buyers combined" : ""}.`}
            items={exportItems(cty, 10)} valueFormat={(v) => `$${fmt(v, v < 10 ? 1 : 0)}bn`}
            sources={[cty.source]} asOf={`12 months to ${periodLabel(cty.as_of)}`} table={exportTable(cty, 12)} />
        )}
        {ind && (
          <BarCard title="What the economy produces" subtitle="Output by industry, share of the total over the past year"
            takeaway={`${ind.items[0].label} is the largest single industry at ${fmt(ind.items[0].share ?? 0)}% of output, but services together make up most of the economy.`}
            items={topWithOther(ind, 10, "All other industries").map((i) => ({ label: i.label, value: i.share ?? 0, color: i.key === "other" ? t.axisMuted : t.s1, extra: `$${fmt(i.value, 0)}bn` }))}
            valueFormat={(v) => pct(v)}
            sources={[ind.source]} asOf={`year to ${periodLabel(ind.as_of, "Q")}`}
            table={{ head: ["Industry", "Share", "$bn"], rows: ind.items.map((i) => [i.label, pct(i.share ?? 0), fmt(i.value, 0)]), num: [1, 2] }} />
        )}
        {S.terms_of_trade && (
          <LineCard title="Terms of trade" subtitle="Export prices relative to import prices (index)"
            takeaway="When this is high, the world pays more for what Australia sells, which boosts incomes and tax revenue."
            lines={[{ s: S.terms_of_trade, name: "Terms of trade", color: t.s1 }]} start="2000-01-01" yFormat={(v) => fmt(v, 0)} />
        )}
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------- 3

export function BudgetSection({ data }: { data: Data }) {
  const t = useTokens();
  const { series: S, bundles: B } = data;
  const rev = B.revenue_mix;
  const exp = B.spending_by_function;
  const bal = S.budget_balance_pct_gdp;
  const debt = S.net_debt_pct_gdp;
  return (
    <Section id="budget" title="How does the government make and spend money?"
      lede={`The federal budget${rev ? ` for ${rev.as_of}` : ""}: where the money comes from, where it goes, and whether it adds up.`}>
      <div className="grid-2">
        {rev && (
          <BarCard title="Where the money comes from" subtitle={`Federal receipts by source, $bn (${rev.as_of} estimate, total ${billions(rev.total ?? 0, 0)})`}
            takeaway={`Nearly half (${fmt(rev.items[0].share ?? 0, 0)}%) comes from income tax paid by individuals. Companies pay ${fmt(rev.items[1].share ?? 0, 0)}%.`}
            items={[...rev.items].sort((a, b) => b.value - a.value).map((i) => ({ label: i.label, value: i.value, color: t.s1, extra: `${pct(i.share ?? 0)} of receipts` }))}
            valueFormat={(v) => `$${fmt(v, 0)}bn`} sources={[rev.source]}
            table={{ head: ["Source", "$bn", "Share"], rows: rev.items.map((i) => [i.label, fmt(i.value), pct(i.share ?? 0)]), num: [1, 2] }} />
        )}
        {exp && (
          <BarCard title="Where the money goes" subtitle={`Federal spending by purpose, $bn (${exp.as_of} estimate, total ${billions(exp.total ?? 0, 0)})`}
            takeaway={`Welfare is the biggest item at ${fmt(exp.items[0].share ?? 0, 0)}%. "Other purposes" is mostly GST passed to the states and interest on debt.`}
            items={topWithOther(exp, 8, "Everything else").map((i) => ({ label: i.label, value: i.value, color: i.key === "other" ? t.axisMuted : t.s1, extra: `${pct(i.share ?? 0)} of spending` }))}
            valueFormat={(v) => `$${fmt(v, 0)}bn`} sources={[exp.source]}
            table={{ head: ["Purpose", "$bn", "Share"], rows: exp.items.map((i) => [i.label, fmt(i.value), pct(i.share ?? 0)]), num: [1, 2] }} />
        )}
        {bal && (
          <ColumnCard title="Surplus or deficit" subtitle="Underlying cash balance, % of GDP, by financial year"
            takeaway={`Last actual: ${signed(actuals(bal).at(-1)![1], 1, "%")} of GDP. Treasury expects deficits every year to ${periodLabel(last(bal)[0], "FY")}.`}
            s={bal} start="1990-01-01" name="Balance" yFormat={(v) => `${fmt(v, 0)}%`} />
        )}
        {debt && (
          <LineCard title="Government debt" subtitle="Net debt, % of GDP, by financial year"
            takeaway={`Net debt is ${pct(actuals(debt).at(-1)![1])} of GDP and forecast to reach ${pct(last(debt)[1])} by ${periodLabel(last(debt)[0], "FY")}.`}
            lines={[{ s: debt, name: "Net debt", color: t.s1 }]} start="1990-01-01" yFormat={(v) => `${fmt(v, 0)}%`} zeroLine />
        )}
      </div>
    </Section>
  );
}

// ---------------------------------------------------------------- 4

export function YouSection({ data }: { data: Data }) {
  const t = useTokens();
  const { series: S, bundles: B } = data;
  const cpiB = B.cpi_breakdown;
  const wage = S.wpi_yoy ? last(S.wpi_yoy)[1] : undefined;
  const cpi = S.cpi_yoy ? last(S.cpi_yoy)[1] : undefined;
  const houses = B.dwelling_price_by_state;
  const ads = B.job_ads_by_occupation;

  const fasterThanWages = cpiB && wage !== undefined ? cpiB.items.filter((i) => i.value > wage) : [];
  const adsBig = ads ? ads.items.filter((i) => i.value >= 2000 && i.change_pct != null) : [];
  const risers = [...adsBig].sort((a, b) => b.change_pct! - a.change_pct!).slice(0, 6);
  const fallers = [...adsBig].sort((a, b) => a.change_pct! - b.change_pct!).slice(0, 6).reverse();
  const housesSorted = houses ? [...houses.items].sort((a, b) => (b.change ?? 0) - (a.change ?? 0)) : [];

  return (
    <Section id="you" title="What does it mean for me?"
      lede="Cost of living, borrowing, housing and jobs. This describes the data; it isn't financial advice.">
      <div className="grid-2">
        {cpiB && (
          <BarCard title="What's getting more expensive" subtitle="Annual price change by category"
            takeaway={wage !== undefined
              ? `${fasterThanWages.length} of ${cpiB.items.length} categories are rising faster than wages (${signed(wage, 1, "%")}), led by ${fasterThanWages.slice(0, 2).map((i) => lc(i.label)).join(" and ")}. Overall prices are up ${signed(cpi ?? 0, 1, "%")}.`
              : undefined}
            items={cpiB.items.map((i) => ({ label: i.label, value: i.value, color: wage !== undefined && i.value > wage ? t.s2 : t.axisMuted }))}
            valueFormat={(v) => signed(v, 1, "%")}
            legend={[{ label: `Rising faster than wages (${signed(wage ?? 0, 1, "%")})`, color: t.s2, kind: "rect" }, { label: "Rising slower than wages", color: t.axisMuted, kind: "rect" }]}
            sources={[cpiB.source]} asOf={periodLabel(cpiB.as_of)}
            table={{ head: ["Category", "Annual change"], rows: cpiB.items.map((i) => [i.label, signed(i.value, 1, "%")]), num: [1] }} />
        )}
        {S.mortgage_rate_discounted && S.cash_rate && (
          <LineCard title="Borrowing costs" subtitle="Per cent per year"
            takeaway={`A typical new variable mortgage costs ${pct(last(S.mortgage_rate_discounted)[1], 2)}. Banks move these rates when the RBA moves the cash rate.`}
            lines={[
              { s: S.mortgage_rate_discounted, name: "Variable mortgage (discounted)", color: t.s1 },
              { s: S.cash_rate, name: "RBA cash rate", color: t.s2, step: true, points: withToday(S.cash_rate).points },
            ]}
            start="2015-01-01" yFormat={(v) => pct(v, v % 1 === 0 ? 0 : 1)} />
        )}
        {houses && (
          <BarCard title="Home prices by state" subtitle="Mean dwelling price, $'000"
            takeaway={`Fastest rises over the year: ${housesSorted.slice(0, 2).map((i) => `${i.label} (${signed(i.change ?? 0, 1, "%")})`).join(" and ")}. Slowest: ${housesSorted.at(-1)?.label} (${signed(housesSorted.at(-1)?.change ?? 0, 1, "%")}).`}
            items={[...houses.items].sort((a, b) => b.value - a.value).map((i) => ({ label: i.label, value: i.value, color: t.s1, extra: `${signed(i.change ?? 0, 1, "%")} vs a year ago` }))}
            valueFormat={(v) => `$${fmt(v, 0)}k`} sources={[houses.source]} asOf={periodLabel(houses.as_of, "Q")}
            table={{ head: ["State", "Mean price ($'000)", "Change on a year ago"], rows: houses.items.map((i) => [i.label, fmt(i.value, 0), signed(i.change ?? 0, 1, "%")]), num: [1, 2] }} />
        )}
        {ads && (
          <BarCard title="Where the jobs are" subtitle="Change in online job ads over the year, occupations with 2,000+ ads a month"
            takeaway={risers.length ? `Growing fastest: ${risers.slice(0, 2).map((i) => lc(i.label)).join(" and ")}. Shrinking most: ${fallers.at(-1)?.label && lc(fallers.at(-1)!.label)}.` : undefined}
            items={[...risers, ...fallers].map((i) => ({ label: i.label, value: i.change_pct!, color: i.change_pct! >= 0 ? t.divPos : t.divNeg, extra: `${fmt(i.value, 0)} ads a month` }))}
            valueFormat={(v) => signed(v, 0, "%")}
            legend={[{ label: "More ads than a year ago", color: t.divPos, kind: "rect" }, { label: "Fewer ads", color: t.divNeg, kind: "rect" }]}
            sources={[ads.source]} asOf={periodLabel(ads.as_of)}
            table={{ head: ["Occupation", "Ads a month", "Change on a year ago"], rows: ads.items.map((i) => [i.label, fmt(i.value, 0), signed(i.change_pct ?? 0, 1, "%")]), num: [1, 2] }} />
        )}
      </div>
    </Section>
  );
}
