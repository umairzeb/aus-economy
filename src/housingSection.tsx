// "Housing": what homes cost, how many are being approved, who is borrowing, and rents and debt.
import { last, valueAt, yearAgo, type Data, type Point } from "./data";
import { BarCard, LineCard } from "./cards";
import { fmt, pct, periodLabel, signed } from "./format";
import { Chapter } from "./chapter";
import { housingVerdict } from "./verdicts";
import { useTokens } from "./theme";

/** National Housing Accord: 1.2 million homes over 5 years from mid-2024. */
const ACCORD_PACE = 240000;
const COTALITY_URL = "https://www.cotality.com/au/our-data/indices";

export function HousingSection({ data }: { data: Data }) {
  const t = useTokens();
  const { series: S, bundles: B } = data;
  const price = S.dwelling_mean_price;
  const houses = B.dwelling_price_by_state;
  const approvals = S.dwelling_approvals_12m;
  const owner = S.lending_owner_occupier;
  const investor = S.lending_investor;
  const firstHome = S.lending_first_home_buyer;
  const rents = S.cpi_rents_yoy;
  const wages = S.wpi_yoy;
  const debt = S.household_debt_to_income;

  const priceAgo = price && yearAgo(price);
  const pricePrev = price && price.points.at(-2)?.[1];
  const priceYear = price && priceAgo ? (last(price)[1] / priceAgo - 1) * 100 : undefined;
  const priceQuarter = price && pricePrev ? (last(price)[1] / pricePrev - 1) * 100 : undefined;
  const byQuarter = houses ? [...houses.items].filter((i) => i.change_q != null).sort((a, b) => a.change_q! - b.change_q!) : [];
  const fell = byQuarter.filter((i) => i.change_q! < 0);
  const rose = byQuarter.at(-1);
  const stateText = (i: { label: string; change_q?: number }) => `${i.label} (${signed(i.change_q ?? 0, 1, "%")})`;
  const fellText = fell.length > 1 ? `${fell.slice(0, -1).map(stateText).join(", ")} and ${stateText(fell.at(-1)!)}` : fell.map(stateText).join("");
  // Official prices come out months after the quarter ends, so say where they stop.
  const priceNote = (end: string) => (
    <>
      These official figures end at {end}, so they can miss a recent turn in the market. For monthly figures, see{" "}
      <a href={COTALITY_URL} target="_blank" rel="noopener noreferrer">Cotality's home value indices</a> (a private company).
    </>
  );
  const accordLine: Point[] = approvals ? approvals.points.map(([d]) => [d, ACCORD_PACE]) : [];
  const approvalsGap = approvals ? (last(approvals)[1] / ACCORD_PACE - 1) * 100 : 0;
  const allLoans = owner && investor ? last(owner)[1] + last(investor)[1] : 0;
  const wagesThen = rents && wages ? valueAt(wages, last(rents)[0]) : undefined;
  const debtAgo = debt && yearAgo(debt);

  return (
    <Chapter id="housing" verdict={housingVerdict(data)}>
      <div className="grid-2">
        {price && (
          <LineCard anchor="chart-home-prices" title="Home prices" subtitle="Average value of all homes in Australia, not just those sold, $'000"
            takeaway={`The average home is worth $${fmt(last(price)[1] / 1000, 2)}m (${periodLabel(last(price)[0], "Q")})${priceQuarter === undefined ? "" : `: ${priceQuarter < 0 ? "down" : "up"} ${pct(Math.abs(priceQuarter))} over the quarter`}${priceYear === undefined ? "" : `, and ${pct(Math.abs(priceYear))} ${priceYear < 0 ? "lower" : "higher"} than a year earlier`}.`}
            note={priceNote(periodLabel(last(price)[0], "Q"))}
            lines={[{ s: price, name: "Average home", color: t.s1 }]} yFormat={(v) => `$${fmt(v, 0)}k`} />
        )}
        {houses && (
          <BarCard title="Home prices by state" subtitle="Mean dwelling price, $'000"
            takeaway={`In the ${periodLabel(houses.as_of, "Q")}, ${fell.length ? `prices fell in ${fellText}` : "prices didn't fall in any state"}${rose && rose.change_q! > 0 ? ` and rose most in ${stateText(rose)}` : ""}.`}
            note={priceNote(periodLabel(houses.as_of, "Q"))}
            items={[...houses.items].sort((a, b) => b.value - a.value).map((i) => ({ label: i.label, value: i.value, color: t.s1, extra: `${signed(i.change_q ?? 0, 1, "%")} over the quarter · ${signed(i.change ?? 0, 1, "%")} vs a year ago` }))}
            valueFormat={(v) => `$${fmt(v, 0)}k`} sources={[houses.source]} asOf={periodLabel(houses.as_of, "Q")}
            table={{ head: ["State", "Mean price ($'000)", "Change over the quarter", "Change on a year ago"], rows: houses.items.map((i) => [i.label, fmt(i.value, 0), signed(i.change_q ?? 0, 1, "%"), signed(i.change ?? 0, 1, "%")]), num: [1, 2, 3] }} />
        )}
        {approvals && (
          <LineCard anchor="chart-approvals" title="Homes approved for building" subtitle="Rolling 12-month total. Approvals are plans, not finished homes."
            takeaway={`${fmt(last(approvals)[1], 0)} homes were approved in the 12 months to ${periodLabel(last(approvals)[0])}, ${fmt(Math.abs(approvalsGap), 0)}% ${approvalsGap < 0 ? "below" : "above"} the ${fmt(ACCORD_PACE, 0)} a year in the National Housing Accord, which began in mid-2024.`}
            lines={[
              { s: approvals, name: "Homes approved", color: t.s1 },
              { s: approvals, name: "Accord pace", color: t.s2, points: accordLine, noChange: true },
            ]}
            yFormat={(v) => fmt(v, 0)} />
        )}
        {owner && investor && firstHome && (
          <LineCard anchor="chart-home-loans" title="Who is taking out home loans" subtitle="New loans each quarter, $bn, seasonally adjusted. First home buyers are also counted in owner-occupiers."
            takeaway={`Investors took ${fmt(last(investor)[1] / allLoans * 100, 0)}% of new home lending in the ${periodLabel(last(owner)[0], "Q")}, and first home buyers ${fmt(last(firstHome)[1] / allLoans * 100, 0)}%.`}
            lines={[
              { s: owner, name: "Owner-occupiers", color: t.s1 },
              { s: investor, name: "Investors", color: t.s2 },
              { s: firstHome, name: "First home buyers", color: t.s3 },
            ]}
            yFormat={(v) => `$${fmt(v / 1000, 0)}bn`} />
        )}
        {rents && wages && (
          <LineCard anchor="chart-rents" title="Rents vs wages" subtitle="Annual change. Covers all rents being paid, not just new listings."
            takeaway={wagesThen === undefined ? undefined : `Rents are rising ${last(rents)[1] > wagesThen ? "faster" : "slower"} than wages (${pct(last(rents)[1])} vs ${pct(wagesThen)}).`}
            lines={[{ s: rents, name: "Rents", color: t.s1 }, { s: wages, name: "Wages", color: t.s2 }]}
            yFormat={(v) => pct(v)} zeroLine />
        )}
        {debt && (
          <LineCard anchor="chart-household-debt" title="Household debt" subtitle="Debt as a share of yearly household disposable income, per cent"
            takeaway={`Households owe about $${fmt(last(debt)[1] / 100, 2)} for every $1 of yearly disposable income${debtAgo ? `, compared with $${fmt(debtAgo / 100, 2)} a year earlier` : ""}.`}
            lines={[{ s: debt, name: "Debt to income", color: t.s1 }]} yFormat={(v) => `${fmt(v, 0)}%`} />
        )}
      </div>
    </Chapter>
  );
}
