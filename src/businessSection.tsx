// "For business": borrowing costs by firm size, business churn, insolvencies and job-ad trends.
import { last, valueAt, type Data, type Series } from "./data";
import { BarCard, GroupedCard, LineCard } from "./cards";
import { billions, fmt, pct, periodLabel, signed } from "./format";
import { Section, lc } from "./sections";
import { useTokens } from "./theme";

/** Value a year before the series' latest point. */
const yearEarlier = (s: Series) => {
  const d = last(s)[0];
  return valueAt(s, `${Number(d.slice(0, 4)) - 1}${d.slice(4)}`);
};

export function BusinessSection({ data }: { data: Data }) {
  const t = useTokens();
  const { series: S, bundles: B } = data;
  const small = S.business_rate_small;
  const medium = S.business_rate_medium;
  const large = S.business_rate_large;
  const counts = B.business_counts_by_size;
  const ins = S.insolvencies_12m;
  const lendSmall = S.lending_small_business_12m;
  const lendMedium = S.lending_medium_business_12m;
  const postings = S.job_postings_indeed;
  const ads = B.job_postings_by_category;

  const withChange = ads ? ads.items.filter((i) => i.change_pct != null) : [];
  const growing = withChange.slice(0, 6);
  const shrinking = withChange.slice(-6);
  // "5–19 staff", "20–199 staff" -> "5–19, 20–199 and 200+ staff"
  const closingBands = counts ? counts.items.filter((i) => (i.exit_rate ?? 0) > (i.entry_rate ?? 0)).map((i) => lc(i.label)) : [];
  const staffed = closingBands.filter((b) => b.endsWith(" staff")).map((b) => b.replace(/ staff$/, ""));
  const closingMore = [
    ...closingBands.filter((b) => !b.endsWith(" staff")),
    ...(staffed.length ? [`${staffed.length > 1 ? `${staffed.slice(0, -1).join(", ")} and ${staffed.at(-1)}` : staffed[0]} staff`] : []),
  ];
  const insAgo = ins && yearEarlier(ins);
  const postingsAgo = postings && yearEarlier(postings);

  return (
    <Section id="business" title="For business"
      lede="What it costs to borrow, how small firms fare against big ones, how many companies are going under, and where hiring is heading.">
      <div className="grid-2">
        {small && medium && large && (
          <LineCard anchor="chart-business-rates" title="What businesses pay to borrow" subtitle="Average interest rate on new business loans, per cent"
            takeaway={`Small businesses pay ${fmt(last(small)[1] - last(large)[1], 1)} percentage points more than large ones (${pct(last(small)[1], 2)} vs ${pct(last(large)[1], 2)}).`}
            lines={[
              { s: small, name: "Small", color: t.s1 },
              { s: medium, name: "Medium", color: t.s2 },
              { s: large, name: "Large", color: t.s3 },
            ]}
            yFormat={(v) => pct(v, 1)} />
        )}
        {counts && (
          <GroupedCard title="Businesses opening and closing, by size" subtitle={`Share of businesses that started or closed during ${counts.as_of}`}
            takeaway={closingMore.length
              ? `More closed than opened among businesses with ${closingMore.join(" and ")}. The smallest firms churn the most: many start and many stop.`
              : "More businesses opened than closed in every size group."}
            categories={counts.items.map((i) => i.label)}
            series={[
              { name: "Opened (entry rate)", values: counts.items.map((i) => i.entry_rate ?? 0), color: t.s1 },
              { name: "Closed (exit rate)", values: counts.items.map((i) => i.exit_rate ?? 0), color: t.s2 },
            ]}
            valueFormat={(v) => pct(v)} sources={[counts.source]} asOf={`financial year ${counts.as_of}`}
            table={{
              head: ["Size", "Operating at end of year", "Opened", "Closed", "Change"],
              rows: counts.items.map((i) => [i.label, fmt(i.value, 0), pct(i.entry_rate ?? 0), pct(i.exit_rate ?? 0), signed(i.change_pct ?? 0, 1, "%")]),
              num: [1, 2, 3, 4],
            }} />
        )}
        {ins && (
          <LineCard anchor="chart-insolvencies" title="Companies going under" subtitle="Companies entering administration for the first time, rolling 12-month total"
            takeaway={`${fmt(last(ins)[1], 0)} companies in the 12 months to ${periodLabel(last(ins)[0])}${insAgo ? `, ${signed((last(ins)[1] / insAgo - 1) * 100, 0, "%")} on a year earlier` : ""}.`}
            lines={[{ s: ins, name: "Companies (12 months)", color: t.s1 }]} yFormat={(v) => fmt(v, 0)} />
        )}
        {lendSmall && lendMedium && (
          <LineCard title="New lending to businesses" subtitle="New loans over the past 12 months, $bn. The ABS publishes no split for large firms."
            takeaway={`Banks lent ${billions(last(lendSmall)[1])} to small businesses and ${billions(last(lendMedium)[1])} to medium ones over the past year.`}
            lines={[
              { s: lendSmall, name: "Small businesses", color: t.s1 },
              { s: lendMedium, name: "Medium businesses", color: t.s2 },
            ]}
            yFormat={(v) => `$${fmt(v, 0)}bn`} />
        )}
        {postings && (
          <LineCard title="Job ads (Indeed)" subtitle="Job ads on Indeed, 1 Feb 2020 = 100, seasonally adjusted. Not an official statistic."
            takeaway={`Job ads are ${fmt(last(postings)[1] - 100, 0)}% above their pre-COVID level${postingsAgo ? ` and ${signed((last(postings)[1] / postingsAgo - 1) * 100, 0, "%")} on a year ago` : ""}.`}
            lines={[{ s: postings, name: "Job ads", color: t.s1 }]} yFormat={(v) => fmt(v, 0)} />
        )}
        {ads && (
          <BarCard title="Which job ads are growing (Indeed)" subtitle="Change in job ads over the year, by type of job. Not an official statistic."
            takeaway={growing.length
              ? `Most growth: ${growing.slice(0, 2).map((i) => lc(i.label)).join(" and ")}. Biggest falls: ${shrinking.slice(-2).map((i) => lc(i.label)).join(" and ")}.`
              : undefined}
            items={[...growing, ...shrinking].map((i) => ({ label: i.label, value: i.change_pct!, color: i.change_pct! >= 0 ? t.divPos : t.divNeg, extra: `Index ${fmt(i.value, 0)} (Feb 2020 = 100)` }))}
            valueFormat={(v) => signed(v, 0, "%")}
            legend={[{ label: "More ads than a year ago", color: t.divPos, kind: "rect" }, { label: "Fewer", color: t.divNeg, kind: "rect" }]}
            sources={[ads.source]} asOf={periodLabel(ads.as_of, "D")}
            table={{ head: ["Type of job", "Index (Feb 2020 = 100)", "Change on a year ago"], rows: ads.items.map((i) => [i.label, fmt(i.value, 0), signed(i.change_pct ?? 0, 1, "%")]), num: [1, 2] }} />
        )}
      </div>
    </Section>
  );
}
