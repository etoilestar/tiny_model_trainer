<template>
  <div class="metrics-chart-wrapper">
    <v-chart
      class="chart"
      :option="chartOption"
      :autoresize="true"
    />
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  data: { type: Array, default: () => [] },
  color: { type: String, default: '#409EFF' },
  xLabel: { type: String, default: 'Epoch' },
  yLabel: { type: String, default: 'Value' },
  extraSeries: { type: Array, default: () => [] }
})

const chartOption = computed(() => {
  const xData = props.data.map(d => d.epoch ?? d.step ?? d.x)
  const yData = props.data.map(d => typeof d.value === 'number' ? +d.value.toFixed(6) : d.value)

  const series = [
    {
      name: props.title,
      type: 'line',
      data: yData,
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2, color: props.color },
      areaStyle: {
        color: {
          type: 'linear',
          x: 0, y: 0, x2: 0, y2: 1,
          colorStops: [
            { offset: 0, color: props.color + '40' },
            { offset: 1, color: props.color + '05' }
          ]
        }
      }
    },
    ...props.extraSeries.map((s, i) => ({
      name: s.name,
      type: 'line',
      data: s.data.map(d => typeof d.value === 'number' ? +d.value.toFixed(6) : d.value),
      smooth: true,
      symbol: 'none',
      lineStyle: { width: 2 }
    }))
  ]

  const legendData = [props.title, ...props.extraSeries.map(s => s.name)]

  return {
    title: {
      text: props.title,
      left: 'center',
      textStyle: { fontSize: 14, fontWeight: 600, color: '#303133' }
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
      formatter: (params) => {
        const epoch = params[0]?.axisValue
        let html = `<div style="font-size:12px"><b>${props.xLabel} ${epoch}</b><br/>`
        for (const p of params) {
          html += `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:4px"></span>`
          html += `${p.seriesName}: <b>${p.value ?? '-'}</b><br/>`
        }
        return html + '</div>'
      }
    },
    legend: {
      data: legendData,
      bottom: 0,
      textStyle: { fontSize: 12 }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '12%',
      top: '16%',
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xData,
      name: props.xLabel,
      nameLocation: 'end',
      nameTextStyle: { fontSize: 11, color: '#909399' },
      axisLine: { lineStyle: { color: '#e4e7ed' } },
      axisTick: { show: false },
      axisLabel: { fontSize: 11, color: '#909399' }
    },
    yAxis: {
      type: 'value',
      name: props.yLabel,
      nameTextStyle: { fontSize: 11, color: '#909399' },
      splitLine: { lineStyle: { color: '#f0f0f0', type: 'dashed' } },
      axisLabel: { fontSize: 11, color: '#909399' }
    },
    series,
    color: [props.color, '#e6a23c', '#67c23a', '#f56c6c', '#909399']
  }
})
</script>

<style scoped>
.metrics-chart-wrapper {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  border: 1px solid #ebeef5;
}

.chart {
  width: 100%;
  height: 300px;
}
</style>
