// How a chart shows what kind each value is (frontend.md, Charts): observed solid; forecast on a shaded band
// labelled "Forecast" (today's partial day counts as forecast); a projection's P50 dashed over its P10–P90 band;
// estimated values as hollow points; missing values as gaps; a dashed "Today" line. Every chart builder takes
// its styling from here, so a weather panel and a model's chart read alike.

import { formatDate } from '../dates'
import { isForecast, type Day } from '../tableRows'
import type { Palette } from './palette'
import { forecastShading } from './shading'

export { isForecast }

/** The index of the first forecast (or partial) day, -1 without one */
export function forecastFrom(days: Pick<Day, 'kind'>[]): number {
  return days.findIndex((day) => isForecast(day) || day.kind === 'projection')
}

/** A value as a line series' data item: a hollow point where it's estimated, a gap (null) where it's missing */
export type Point = number | null | { value: number; symbol: string; symbolSize: number; itemStyle: object }

export function point(value: number | null, estimated: boolean, palette: Palette): Point {
  if (value === null || Number.isNaN(value)) return null
  if (!estimated) return value
  return {
    value,
    symbol: 'emptyCircle',
    symbolSize: 6,
    itemStyle: { borderColor: palette.estimated, borderWidth: 1.5, color: palette.surface },
  }
}

/** A bar's data item: hatched-looking (hollow, outlined) where it's estimated */
export function bar(value: number | null, estimated: boolean, color: string, palette: Palette) {
  if (value === null || Number.isNaN(value)) return null
  if (!estimated) return value
  return { value, itemStyle: { color: palette.surface, borderColor: color, borderWidth: 1.5, borderType: 'dashed' } }
}

/** A line series' style for a kind of values: observed and forecast solid (the forecast's band says which is
 * which), a projection dashed */
export function lineStyle(color: string, kind: 'observed' | 'projection' = 'observed', width = 2) {
  return { width, color, type: kind === 'projection' ? ('dashed' as const) : ('solid' as const) }
}

/** A band between two lines (a projection's P10–P90) as two stacked series: the lower edge invisible, the band
 * its height above it, faint */
export function band({
  id,
  lower,
  upper,
  color,
  xAxisIndex = 0,
  yAxisIndex = 0,
}: {
  id: string
  lower: (number | null)[]
  upper: (number | null)[]
  color: string
  xAxisIndex?: number
  yAxisIndex?: number
}): object[] {
  const stack = `band-${id}`
  const common = { type: 'line', stack, symbol: 'none', silent: true, xAxisIndex, yAxisIndex, tooltip: { show: false } }
  return [
    { ...common, id: `${stack}-lower`, name: `${id} lower`, data: lower, lineStyle: { opacity: 0 } },
    {
      ...common,
      id: `${stack}-upper`,
      name: `${id} band`,
      data: upper.map((value, i) => (value === null || lower[i] === null ? null : value - (lower[i] as number))),
      lineStyle: { opacity: 0 },
      areaStyle: { color, opacity: 0.18 },
    },
  ]
}

/** The dashed "Today" line (a markLine on the category axis), when today is one of the dates; given an hour
 * (`2026-11-25T14:00Z`, the latest observed), a "Now" line on it */
export function todayLine(dates: string[], today: string, palette: Palette) {
  const hour = today.length > 10
  const at = dates.find((date) => (hour ? date === today : date.slice(0, 10) === today))
  if (!at) return []
  return [
    {
      xAxis: at,
      lineStyle: { color: palette.ink, type: 'dashed', width: 1, opacity: 0.6 },
      label: { formatter: hour ? 'Now' : 'Today', position: 'end', color: palette.inkMuted, fontSize: 10 },
    },
  ]
}

/** A threshold as a labelled, dashed reference line (32 °F frost, 18 DSV) */
export function thresholdLine(value: number, name: string, palette: Palette) {
  return {
    yAxis: Number(value.toFixed(3)),
    lineStyle: { color: palette.inkMuted, type: 'dashed', width: 1 },
    label: { formatter: name, position: 'insideEndTop', color: palette.inkMuted, fontSize: 10 },
  }
}

/** The forecast's shading across a chart's grids, and the "Forecast" label over it (a transparent markArea on
 * the first series) */
export function forecastBand({
  dates,
  days,
  grids,
  axisOffset,
  palette,
}: {
  dates: string[]
  days: Pick<Day, 'kind'>[]
  grids: number
  axisOffset: number
  palette: Palette
}) {
  const from = forecastFrom(days)
  const shading = forecastShading({ dates, from, grids, axisOffset, palette })
  const label =
    from >= 0
      ? {
          silent: true,
          itemStyle: { opacity: 0 },
          label: { show: true, position: 'insideTop', color: palette.inkMuted, fontSize: 10, formatter: 'Forecast' },
          data: [[{ xAxis: dates[from] }, { xAxis: dates[dates.length - 1] }]],
        }
      : undefined
  return { shading, label }
}

const hourFormats = new Map<string, Intl.DateTimeFormat>()

/** An hour (UTC, as the API gives it) on the location's clock, with its zone: "Nov 25, 2 p.m. CST"; with
 * `short`, "2 p.m." (midnight shows its date: "Nov 25") */
export function formatHour(iso: string, timeZone = 'America/Chicago', { short = false } = {}): string {
  const key = timeZone
  let format = hourFormats.get(key)
  if (!format) {
    format = new Intl.DateTimeFormat('en-US', {
      timeZone,
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      timeZoneName: 'short',
    })
    hourFormats.set(key, format)
  }
  const parts = Object.fromEntries(format.formatToParts(new Date(iso)).map((part) => [part.type, part.value]))
  const meridiem = parts.dayPeriod === 'AM' ? 'a.m.' : 'p.m.'
  const hour = parts.hour === '12' && meridiem === 'p.m.' ? 'noon' : `${parts.hour} ${meridiem}`
  const date = `${parts.month} ${parts.day}`
  if (short) return parts.hour === '12' && meridiem === 'a.m.' ? date : hour === 'noon' ? 'Noon' : hour
  return `${date}, ${hour === 'noon' ? 'noon' : hour} ${parts.timeZoneName}`
}

/** A row's date or hour for an axis, a tooltip or a table */
export function rowLabel(date: string, timeZone?: string, options: { short?: boolean } = {}): string {
  return date.length > 10 ? formatHour(date, timeZone, options) : formatDate(date, { weekday: !options.short })
}
