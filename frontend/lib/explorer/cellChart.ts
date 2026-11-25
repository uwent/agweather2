// The clicked cell's chart (Phase 7 track 2 step 6): a pure ECharts option builder over the cell's series, in the
// reader's units, with the forecast shaded and a dashed line at the map's day; and the same values as a table.

import type { ChartTable } from '@/lib/charts/ChartCard.svelte'
import type { EChartsCoreOption } from '@/lib/charts/echarts'
import { baseOption, type Palette } from '@/lib/charts/palette'
import { forecastShading } from '@/lib/charts/shading'
import { formatDate } from '@/lib/dates'
import { convert, displayUnit, formatNumber, type Units } from '@/lib/units'

import type { CellSeries } from './cellSeries'
import { formatHour } from './words'

/** The series in the reader's units: the API answered in US units, so a value goes from the stored unit's US
 * display unit to the reader's */
export function shownValues(
  series: CellSeries,
  stored: string | null,
  units: Units,
): { values: (number | null)[]; unit: string } {
  if (!stored || series.labels) return { values: series.values, unit: series.unit }
  try {
    const from = displayUnit(stored, 'imperial')
    const to = displayUnit(stored, units.system)
    return { values: series.values.map((v) => convert(v, from, to)), unit: units.label(stored) }
  } catch {
    return { values: series.values, unit: series.unit }
  }
}

const label = (time: string) => (time.length > 10 ? formatHour(time) : formatDate(time))

export function buildCellChart(options: {
  series: CellSeries
  values: (number | null)[]
  unit: string
  name: string
  /** The map's day or hour, marked on the chart */
  marked: string | null
  /** Risk levels' names, for a model's levels (the y axis then names them) */
  levels: string[] | null
  digits: number
}) {
  return (palette: Palette): EChartsCoreOption => {
    const { series, values, unit, name, marked, levels, digits } = options
    const base = baseOption(palette)
    const labels = series.times.map(label)
    const from = series.kinds.findIndex((kind) => kind === 'forecast')
    const shading = forecastShading({ dates: labels, from, grids: 1, axisOffset: 1, palette })
    const markedAt = marked ? series.times.findIndex((t) => t.slice(0, marked.length) === marked) : -1
    const colors = levels?.length === 4 ? palette.probability : palette.severity
    return {
      animation: base.animation,
      textStyle: base.textStyle,
      tooltip: {
        ...base.tooltip,
        valueFormatter: (value: unknown) =>
          typeof value !== 'number'
            ? '—'
            : levels
              ? (levels[value - 1] ?? String(value - 1))
              : `${formatNumber(value, digits)}${unit ? ` ${unit}` : ''}`,
      },
      grid: { top: 28, bottom: 28, left: levels ? 72 : 48, right: 16 },
      xAxis: [{ type: 'category', data: labels, axisLabel: base.axisLabel, axisLine: base.axisLine }, ...shading.xAxis],
      yAxis: [
        levels
          ? {
              type: 'value',
              // A level's bar stands one step high for its lowest, so Very low shows
              min: 0,
              max: levels.length,
              interval: 1,
              axisLabel: { ...base.axisLabel, formatter: (v: number) => levels[v - 1] ?? '' },
              splitLine: base.splitLine,
            }
          : { type: 'value', name: unit, scale: true, axisLabel: base.axisLabel, splitLine: base.splitLine },
        ...shading.yAxis,
      ],
      series: [
        ...shading.series,
        {
          name,
          type: levels ? 'bar' : 'line',
          data: levels
            ? values.map((v) =>
                v === null ? null : { value: v + 1, itemStyle: { color: colors[v] ?? palette.inkMuted } },
              )
            : values,
          color: palette.degreeDays,
          symbol: 'circle',
          symbolSize: 5,
          showSymbol: values.length <= 31,
          lineStyle: { width: 2 },
          connectNulls: false,
          z: 3,
          markLine:
            markedAt >= 0
              ? {
                  silent: true,
                  symbol: 'none',
                  lineStyle: { color: palette.inkMuted, type: 'dashed' },
                  label: { formatter: 'Map', position: 'insideEndTop', color: palette.inkMuted },
                  data: [{ xAxis: markedAt }],
                }
              : undefined,
        },
      ],
    }
  }
}

/** The values as "Summary and data"'s table, newest first */
export function cellTable(
  series: CellSeries,
  values: (number | null)[],
  column: string,
  levels: string[] | null,
  digits: number,
): ChartTable {
  return {
    columns: [column],
    rows: series.times
      .map((time, i) => ({
        date: time.length > 10 ? formatHour(time) : time,
        forecast: series.kinds[i] === 'forecast',
        values: [
          values[i] === null
            ? null
            : levels
              ? (levels[values[i] as number] ?? String(values[i]))
              : formatNumber(values[i], digits),
        ],
      }))
      .reverse(),
  }
}

/** The chart in words: its range and the latest value */
export function cellSummary(
  series: CellSeries,
  values: (number | null)[],
  unit: string,
  levels: string[] | null,
  digits: number,
): string {
  const known = values.map((v, i) => ({ v, i })).filter((p): p is { v: number; i: number } => p.v !== null)
  const step = (series.times[0]?.length ?? 0) > 10 ? 'hour' : 'day'
  if (!known.length) return `No values for these ${step}s.`
  const word = (v: number) =>
    levels ? (levels[v] ?? String(v)) : `${formatNumber(v, digits)}${unit ? ` ${unit}` : ''}`
  const span = `${label(series.times[0])} to ${label(series.times.at(-1)!)}`
  const forecast = series.kinds.filter((k) => k === 'forecast').length
  const lowest = known.reduce((a, b) => (b.v < a.v ? b : a))
  const highest = known.reduce((a, b) => (b.v > a.v ? b : a))
  const missing = values.length - known.length
  return [
    `From ${span}, values run from ${word(lowest.v)} (${label(series.times[lowest.i])}) to ${word(highest.v)} (${label(series.times[highest.i])}).`,
    forecast
      ? forecast === 1
        ? `The last ${step} is a forecast.`
        : `The last ${forecast} ${step}s are a forecast.`
      : '',
    missing ? `${missing} ${missing === 1 ? `${step} has` : `${step}s have`} no value.` : '',
  ]
    .filter(Boolean)
    .join(' ')
}
