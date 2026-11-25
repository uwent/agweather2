// WISP 3: app/frontend/lib/charts/shading.ts (copied)
import type { Palette } from './palette'

// The forecast's shading across a chart's grids. A markArea on a category axis starts and ends at
// the middle of a day (ECharts rounds its coordinates to a category), which leaves half a day
// unshaded at each end. Full-width bars fill whole days instead, edge to edge. They sit on hidden
// axes of their own, so they don't share the day's width with the chart's real bars.

export type Shading = {
  /** Hidden category axes, one per grid, to add after the chart's own x axes */
  xAxis: object[]
  /** Hidden 0–1 value axes, one per grid, to add after the chart's own y axes */
  yAxis: object[]
  series: object[]
  /** The indexes of the hidden x axes, for the chart's dataZoom to move them with the rest */
  xAxisIndexes: number[]
}

/**
 * dates: the chart's categories; from: the index of the first shaded day; grids: how many grids
 * the chart has; axisOffset: how many x and y axes the chart has before these
 */
export function forecastShading({
  dates,
  from,
  grids,
  axisOffset,
  palette,
}: {
  dates: string[]
  from: number
  grids: number
  axisOffset: number
  palette: Palette
}): Shading {
  if (from < 0 || from >= dates.length) return { xAxis: [], yAxis: [], series: [], xAxisIndexes: [] }
  const indexes = Array.from({ length: grids }, (_, grid) => axisOffset + grid)
  return {
    xAxis: indexes.map((_, gridIndex) => ({ type: 'category', data: dates, gridIndex, show: false })),
    yAxis: indexes.map((_, gridIndex) => ({ type: 'value', gridIndex, show: false, min: 0, max: 1 })),
    series: indexes.map((index) => ({
      id: `shading-${index - axisOffset}`,
      name: SHADING,
      type: 'bar',
      xAxisIndex: index,
      yAxisIndex: index,
      data: dates.map((_, i) => (i >= from ? 1 : null)),
      barWidth: '100%',
      itemStyle: { color: palette.inkMuted, opacity: 0.08 },
      silent: true,
      tooltip: { show: false },
      z: 0,
    })),
    xAxisIndexes: indexes,
  }
}

export const SHADING = 'Forecast shading'
