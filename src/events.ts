// Major events marked on long time-series charts so the bumps explain themselves.
export interface EconEvent {
  date: string;
  label: string;
  /** Shorter label for narrow charts. */
  short: string;
}

export const EVENTS: EconEvent[] = [
  { date: "2000-07-01", label: "GST introduced", short: "GST" },
  { date: "2008-09-15", label: "Global financial crisis", short: "GFC" },
  { date: "2011-09-30", label: "Mining boom peak", short: "Mining peak" },
  { date: "2020-03-31", label: "COVID-19", short: "COVID" },
  { date: "2022-05-03", label: "RBA starts raising rates", short: "Rate hikes" },
];

export const eventsBetween = (start: string, end: string) => EVENTS.filter((e) => e.date >= start && e.date <= end);
