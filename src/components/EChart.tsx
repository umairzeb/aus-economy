import { useEffect, useRef, useState } from "react";
import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, MarkAreaComponent, MarkLineComponent, TooltipComponent } from "echarts/components";
import { LabelLayout } from "echarts/features";
import { SVGRenderer } from "echarts/renderers";
import type { EChartsOption } from "echarts";

echarts.use([LineChart, BarChart, GridComponent, TooltipComponent, MarkAreaComponent, MarkLineComponent, LabelLayout, SVGRenderer]);

interface Props {
  /** Built from the container width so labels and spacing adapt to phones. */
  option: (width: number) => EChartsOption;
  height: number;
  label: string;
}

export function EChart({ option, height, label }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const [width, setWidth] = useState(0);

  useEffect(() => {
    const el = ref.current!;
    chart.current = echarts.init(el, undefined, { renderer: "svg" });
    const ro = new ResizeObserver(() => {
      setWidth(el.clientWidth);
      chart.current?.resize();
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
      chart.current?.dispose();
      chart.current = null;
    };
  }, []);

  useEffect(() => {
    if (chart.current && width > 0) chart.current.setOption(option(width), true);
  }, [option, width]);

  return <div ref={ref} style={{ width: "100%", height }} role="img" aria-label={label} />;
}
