// A chapter: numbered header with a one-line plain-English verdict, optional key numbers, then its charts.
import type { ReactNode } from "react";
import { StatTile, type TileProps } from "./components/ui";

export type Part = "Your wallet" | "The country" | "Government and business";

export const CHAPTERS = [
  { id: "cost", n: 1, title: "Cost of living", short: "Cost of living", part: "Your wallet" },
  { id: "jobs", n: 2, title: "Jobs and pay", short: "Jobs", part: "Your wallet" },
  { id: "rates", n: 3, title: "Interest rates and loans", short: "Rates", part: "Your wallet" },
  { id: "housing", n: 4, title: "Housing", short: "Housing", part: "Your wallet" },
  { id: "economy", n: 5, title: "The economy", short: "Economy", part: "The country" },
  { id: "budget", n: 6, title: "Government money", short: "Government", part: "Government and business" },
  { id: "business", n: 7, title: "Business", short: "Business", part: "Government and business" },
] as const satisfies readonly { id: string; n: number; title: string; short: string; part: Part }[];

export type ChapterId = (typeof CHAPTERS)[number]["id"];

/** Tiles for the given ids, in that order, skipping any without data. */
export const pick = (tiles: TileProps[], ...ids: string[]): TileProps[] =>
  ids.map((id) => tiles.find((t) => t.id === id)).filter((t): t is TileProps => !!t);

export function Chapter({ id, verdict, tiles, children }: { id: ChapterId; verdict?: string; tiles?: TileProps[]; children: ReactNode }) {
  const c = CHAPTERS.find((x) => x.id === id)!;
  return (
    <section className="chapter" id={id} aria-labelledby={`${id}-h`}>
      <header>
        <div className="eyebrow"><span className="badge" aria-hidden="true">{c.n}</span>{c.part}</div>
        <h2 id={`${id}-h`}>{c.title}</h2>
        {verdict && <p className="verdict">{verdict}</p>}
        {tiles && tiles.length > 0 && (
          <div className="tiles tiles-chapter">{tiles.map((t) => <StatTile key={t.label} {...t} />)}</div>
        )}
      </header>
      {children}
    </section>
  );
}
