// ECharts option builders. Mark specs follow the dataviz skill: 2px lines,
// bars <= 18px with 4px rounded data-ends, hairline solid grid, text in ink
// tokens (never series colours), one y-axis per chart.
import type { EChartsOption, LineSeriesOption, BarSeriesOption } from "echarts";
import type { Point } from "./data";
import { escapeHtml, periodLabel } from "./format";
import type { Tokens } from "./theme";

const FONT = 'system-ui, -apple-system, "Segoe UI", sans-serif';

/** Axis ticks drop a trailing ".0": "15.0%" -> "15%". */
const tick = (s: string) => s.replace(/\.0(?=\D*$)/, "");

function tooltipBase(t: Tokens) {
  return {
    backgroundColor: t.surface,
    borderColor: t.border,
    borderWidth: 1,
    padding: [8, 10] as [number, number],
    confine: true,
    textStyle: { color: t.textSecondary, fontFamily: FONT },
    extraCssText: "box-shadow:0 4px 16px rgba(0,0,0,.14);border-radius:8px;",
  };
}

const ttRow = (color: string, value: string, name: string, rect = false) =>
  `<div class="tt-row"><span class="tt-key${rect ? " rect" : ""}" style="background:${color}"></span>` +
  `<strong>${escapeHtml(value)}</strong><span>${escapeHtml(name)}</span></div>`;

// ---------- Line charts ----------

export interface LineSpec {
  name: string;
  points: Point[];
  color: string;
  step?: boolean;
  /** Points on/after this date are drawn dashed as forecasts. */
  forecastFrom?: string | null;
}

export interface LineOpts {
  series: LineSpec[];
  t: Tokens;
  width: number;
  freq: string;
  yFormat: (v: number) => string;
  band?: [number, number];
  bandLabel?: string;
  breaks?: { date: string; label: string }[];
  zeroLine?: boolean;
  endLabels?: boolean;
}

export function lineOption(o: LineOpts): EChartsOption {
  const { t } = o;
  const all = o.series.flatMap((s) => s.points);
  const years = all.length ? (Date.parse(all[all.length - 1][0]) - Date.parse(all[0][0])) / 3.15e10 : 0;
  const narrow = o.width < 480;

  const out: LineSeriesOption[] = [];
  o.series.forEach((s, i) => {
    const actual = s.forecastFrom ? s.points.filter(([d]) => d < s.forecastFrom!) : s.points;
    const forecast = s.forecastFrom ? s.points.filter(([d]) => d >= s.forecastFrom!) : [];
    const base: LineSeriesOption = {
      type: "line",
      name: s.name,
      showSymbol: false,
      symbolSize: 8,
      step: s.step ? "end" : undefined,
      sampling: "lttb",
      lineStyle: { width: 2, color: s.color, cap: "round", join: "round" },
      itemStyle: { color: s.color, borderColor: t.surface, borderWidth: 2 },
      emphasis: { disabled: true },
      z: 3,
    };
    out.push({
      ...base,
      id: `${s.name}-actual`,
      data: actual,
      endLabel: o.endLabels && !forecast.length
        ? { show: true, formatter: (p) => o.yFormat((p.value as Point)[1]), color: t.textSecondary, fontSize: 12, fontFamily: FONT, distance: 6 }
        : undefined,
      markArea: i === 0 && o.band
        ? {
            silent: true,
            itemStyle: { color: t.band },
            label: { show: !!o.bandLabel, formatter: o.bandLabel, position: "insideTopLeft", color: t.textMuted, fontSize: 11, fontFamily: FONT },
            data: [[{ yAxis: o.band[0] }, { yAxis: o.band[1] }]],
          }
        : undefined,
      markLine: i === 0 && (o.breaks?.length || o.zeroLine)
        ? {
            silent: true,
            symbol: "none",
            lineStyle: { color: t.axis, width: 1, type: "solid" },
            label: { color: t.textMuted, fontSize: 11, fontFamily: FONT },
            data: [
              ...(o.zeroLine ? [{ yAxis: 0, label: { show: false } }] : []),
              ...(o.breaks ?? []).map((b) => ({
                xAxis: b.date,
                label: { show: true, formatter: narrow ? "New CPI" : b.label, position: "insideEndTop" as const },
              })),
            ],
          }
        : undefined,
    });
    if (forecast.length && actual.length) {
      out.push({
        ...base,
        id: `${s.name}-forecast`,
        data: [actual[actual.length - 1], ...forecast],
        lineStyle: { ...base.lineStyle, type: "dashed" },
        endLabel: o.endLabels
          ? { show: true, formatter: (p) => o.yFormat((p.value as Point)[1]), color: t.textSecondary, fontSize: 12, fontFamily: FONT, distance: 6 }
          : undefined,
      });
    }
  });

  return {
    animation: false,
    textStyle: { fontFamily: FONT },
    grid: { left: 4, right: o.endLabels ? 48 : 12, top: 16, bottom: 4 },
    xAxis: {
      type: "time",
      axisLine: { lineStyle: { color: t.axis } },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: {
        color: t.axisMuted,
        hideOverlap: true,
        formatter: (v: number) => {
          const d = new Date(v);
          return years > 3 ? String(d.getFullYear()) : d.toLocaleDateString("en-AU", { month: "short", year: "2-digit" });
        },
      },
    },
    yAxis: {
      type: "value",
      scale: true,
      splitNumber: 4,
      axisLabel: { color: t.axisMuted, formatter: (v: number) => tick(o.yFormat(v)) },
      splitLine: { lineStyle: { color: t.grid, width: 1, type: "solid" } },
    },
    tooltip: {
      ...tooltipBase(t),
      trigger: "axis",
      axisPointer: { type: "line", lineStyle: { color: t.axis, width: 1 } },
      formatter: (raw) => {
        const ps = (Array.isArray(raw) ? raw : [raw]) as unknown as { seriesName: string; color: string; value: Point; seriesId: string }[];
        if (!ps.length) return "";
        const seen = new Set<string>();
        const rows = ps
          .filter((p) => !seen.has(p.seriesName) && seen.add(p.seriesName))
          .map((p) => ttRow(p.color, o.yFormat(p.value[1]), p.seriesName + (p.seriesId.endsWith("-forecast") ? " (forecast)" : "")));
        return `<div class="tt"><div class="tt-head">${periodLabel(ps[0].value[0], o.freq)}</div>${rows.join("")}</div>`;
      },
    },
    series: out,
  };
}

// ---------- Horizontal bar lists ----------

export interface BarItem {
  label: string;
  value: number;
  color: string;
  /** Extra tooltip line, e.g. "35% of exports · +11% on last year". */
  extra?: string;
}

export interface RefLine {
  value: number;
  label: string;
  position?: "start" | "end";
}

export interface BarOpts {
  items: BarItem[];
  t: Tokens;
  width: number;
  valueFormat: (v: number) => string;
  refLines?: RefLine[];
}

export const barListHeight = (n: number, refLines = 0) => n * 30 + 16 + (refLines ? 36 : 0);

export function barOption(o: BarOpts): EChartsOption {
  const { t } = o;
  const labelWidth = Math.round(Math.min(210, Math.max(100, o.width * 0.44)));
  const hasNeg = o.items.some((i) => i.value < 0);
  const data: BarSeriesOption["data"] = o.items.map((i) => ({
    value: i.value,
    name: i.label,
    itemStyle: { color: i.color, borderRadius: i.value >= 0 ? [0, 4, 4, 0] : [4, 0, 0, 4] },
    label: { position: i.value >= 0 ? "right" : "left" },
  }));
  const ref = o.refLines ?? [];
  return {
    animation: false,
    textStyle: { fontFamily: FONT },
    grid: { left: 4, right: 52, top: ref.length ? 22 : 4, bottom: ref.length ? 18 : 4 },
    xAxis: { type: "value", show: false, min: hasNeg ? undefined : 0 },
    yAxis: {
      type: "category",
      inverse: true,
      data: o.items.map((i) => i.label),
      axisTick: { show: false },
      axisLine: { show: true, lineStyle: { color: t.axis } },
      axisLabel: { color: t.textSecondary, fontSize: 12, width: labelWidth, overflow: "truncate", margin: 8 },
    },
    tooltip: {
      ...tooltipBase(t),
      trigger: "item",
      formatter: (p) => {
        const i = o.items[(p as { dataIndex: number }).dataIndex];
        return `<div class="tt">${ttRow(i.color, o.valueFormat(i.value), i.label, true)}${i.extra ? `<div class="tt-extra">${escapeHtml(i.extra)}</div>` : ""}</div>`;
      },
    },
    series: [
      {
        type: "bar",
        data,
        barMaxWidth: 18,
        barCategoryGap: "32%",
        label: { show: true, color: t.textSecondary, fontSize: 12, formatter: (p) => o.valueFormat(p.value as number), distance: 6 },
        emphasis: { itemStyle: { opacity: 0.85 } },
        markLine: ref.length
          ? {
              silent: true,
              symbol: "none",
              lineStyle: { color: t.textMuted, width: 1, type: "solid" },
              data: ref.map((r) => ({
                xAxis: r.value,
                label: {
                  formatter: r.label,
                  position: r.position === "start" ? "insideStartTop" : "end",
                  color: t.textSecondary,
                  fontSize: 11,
                  fontFamily: FONT,
                },
              })),
            }
          : undefined,
      },
    ],
  };
}

// ---------- Column chart for financial years (budget) ----------

export interface ColumnOpts {
  points: Point[];
  forecastFrom?: string | null;
  t: Tokens;
  width: number;
  yFormat: (v: number) => string;
  name: string;
}

export function columnOption(o: ColumnOpts): EChartsOption {
  const { t } = o;
  const isF = (d: string) => !!o.forecastFrom && d >= o.forecastFrom;
  return {
    animation: false,
    textStyle: { fontFamily: FONT },
    grid: { left: 4, right: 8, top: 12, bottom: 4 },
    xAxis: {
      type: "category",
      data: o.points.map(([d]) => periodLabel(d, "FY")),
      axisTick: { show: false },
      axisLine: { show: false },
      axisLabel: { color: t.axisMuted, hideOverlap: true, interval: o.width < 480 ? 9 : 4 },
    },
    yAxis: {
      type: "value",
      splitNumber: 4,
      axisLabel: { color: t.axisMuted, formatter: (v: number) => o.yFormat(v) },
      splitLine: { lineStyle: { color: t.grid, width: 1, type: "solid" } },
    },
    tooltip: {
      ...tooltipBase(t),
      trigger: "axis",
      axisPointer: { type: "shadow", shadowStyle: { color: t.grid, opacity: 0.4 } },
      formatter: (raw) => {
        const p = (Array.isArray(raw) ? raw[0] : raw) as { dataIndex: number };
        const [d, v] = o.points[p.dataIndex];
        const f = isF(d);
        return `<div class="tt"><div class="tt-head">${periodLabel(d, "FY")}${f ? " · Treasury forecast" : ""}</div>${ttRow(f ? t.s1Soft : t.s1, o.yFormat(v), o.name, true)}</div>`;
      },
    },
    series: [
      {
        type: "bar",
        barMaxWidth: 14,
        barCategoryGap: "24%",
        data: o.points.map(([d, v]) => ({
          value: v,
          itemStyle: { color: isF(d) ? t.s1Soft : t.s1, borderRadius: v >= 0 ? [4, 4, 0, 0] : [0, 0, 4, 4] },
        })),
        markLine: { silent: true, symbol: "none", lineStyle: { color: t.axis, width: 1, type: "solid" }, label: { show: false }, data: [{ yAxis: 0 }] },
      },
    ],
  };
}
