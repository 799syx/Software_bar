<script setup lang="ts">
import { BarChart, LineChart, PieChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { init, use, type ECharts } from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { onBeforeUnmount, onMounted, ref, watch } from "vue";

use([BarChart, LineChart, PieChart, GridComponent, TooltipComponent, CanvasRenderer]);

const props = withDefaults(defineProps<{
  title: string;
  labels: string[];
  values: number[];
  kind: "line" | "bar" | "pie";
  color?: string;
  showYGrid?: boolean;
}>(), {
  showYGrid: true
});

const root = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

function renderChart() {
  if (!root.value) return;
  if (!chart) chart = init(root.value);
  const color = props.color || "#2f6d52";
  const textColor = "#22362f";
  const gridColor = "rgba(34, 54, 47, 0.12)";

  const option =
    props.kind === "pie"
      ? {
          tooltip: { trigger: "item" },
          color: [color, "#7aa391", "#d88b5d", "#87a9c4", "#c5a658"],
          series: [
            {
              name: props.title,
              type: "pie",
              radius: ["45%", "72%"],
              avoidLabelOverlap: true,
              label: { color: textColor, formatter: "{b}" },
              data: props.labels.map((label, index) => ({ name: label, value: props.values[index] || 0 }))
            }
          ]
        }
      : {
          tooltip: { trigger: "axis" },
          grid: { left: 42, right: 20, top: 24, bottom: 38, containLabel: true },
          xAxis: {
            type: "category",
            data: props.labels,
            axisLine: { lineStyle: { color: gridColor } },
            axisLabel: { color: "rgba(34, 54, 47, 0.68)", hideOverlap: true }
          },
          yAxis: {
            type: "value",
            scale: props.kind === "line",
            splitLine: { show: props.showYGrid, lineStyle: { color: gridColor } },
            axisLabel: { color: "rgba(34, 54, 47, 0.68)", hideOverlap: true }
          },
          color: [color],
          series: [
            {
              name: props.title,
              type: props.kind,
              smooth: true,
              barWidth: 18,
              areaStyle: props.kind === "line" ? { color: "rgba(47, 109, 82, 0.12)" } : undefined,
              data: props.values
            }
          ]
        };

  chart.setOption(option as never, true);
}

function resizeChart() {
  chart?.resize();
}

onMounted(() => {
  renderChart();
  window.addEventListener("resize", resizeChart);
});

onBeforeUnmount(() => {
  window.removeEventListener("resize", resizeChart);
  chart?.dispose();
});

watch(() => [props.labels, props.values, props.kind, props.color, props.showYGrid], renderChart, { deep: true });
</script>

<template>
  <div class="chart-panel">
    <h3>{{ title }}</h3>
    <div ref="root" class="chart-root"></div>
  </div>
</template>
