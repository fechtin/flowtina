<script setup lang="ts">
import { computed } from 'vue'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  LegendComponent,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import VChart from 'vue-echarts'
import { useSettingsStore } from '@/stores/settings'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const props = defineProps<{ labels: string[]; values: number[]; name: string }>()
const settings = useSettingsStore()

const option = computed(() => {
  const dark = settings.theme === 'dark'
  const axisColor = dark ? '#9ca3af' : '#6b7280'
  const splitColor = dark ? '#1f2937' : '#f3f4f6'
  return {
    grid: { left: 40, right: 16, top: 24, bottom: 32 },
    tooltip: { trigger: 'axis' },
    xAxis: {
      type: 'category',
      data: props.labels,
      boundaryGap: false,
      axisLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
    },
    series: [
      {
        name: props.name,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        data: props.values,
        lineStyle: { color: '#1f59ea', width: 3 },
        itemStyle: { color: '#1f59ea' },
        areaStyle: {
          color: {
            type: 'linear',
            x: 0,
            y: 0,
            x2: 0,
            y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(31,89,234,0.25)' },
              { offset: 1, color: 'rgba(31,89,234,0)' },
            ],
          },
        },
      },
    ],
  }
})
</script>

<template>
  <VChart class="h-72 w-full" :option="option" autoresize />
</template>
