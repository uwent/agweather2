// Climate's charts (Phase 7 track 6.1): a place against its normal, and its freeze odds. Pure builders over the
// API's column names, shared by the site's Climate tab, `/climate` and the tools (the freeze tool, crop GDD, the
// alfalfa planner), so their signatures are fixed in the plan (docs/plans/phase-7-web-app.md, "Track 6 in detail").
//
//   normalBand({ id, dates, mean, low, high, color, name })     // a normal with its 10th–90th percentile band
//   const table = compareTable(body)                            // `/climate/compare`'s answer
//   compareOption({ table, column, units, palette, today, label, lastYear })
//   compareSummary({ table, column, units, label })             // the chart in words
//   const chances = freezeChances(body)                         // `/climate/frost/chances`'s long table
//   freezeOddsOption({ chances, thresholds, show, today, units, palette })
//   const dates = freezeDates(body)                             // `/climate/frost`'s dates
//   freezeSummary({ dates, units, show })                       // the odds in words
//
// Values stay in the units the answer gives (pages ask with `units=us`) and are converted at display.

import type { TableResponse } from '@/types/api'

import { daysAheadWords, ordinal, percentileWords, shareOfYears, thresholdLabel, thresholdNoun } from '../climate/words'
import { periodWords, summaryYears, type PeriodYears } from '../climate/periods'
import { formatDate } from '../dates'
import { columnsOf, unitSymbol, type Kind } from '../tableRows'
import type { Units } from '../units'
import type { EChartsCoreOption } from './echarts'
import { band, rounded, rowLabel, thresholdLine, todayLine } from './kinds'
import { baseOption, type Palette } from './palette'
import { forecastShading } from './shading'

type Body = Pick<TableResponse, 'meta' | 'data'>

/**
 * A normal as a dashed line over its spread: the band between `low` and `high` (the 10th and 90th percentiles),
 * faint, then the mean. Values are as drawn (already in display units). The band's two series stay out of the
 * tooltip; the line is named `name`, the band `${name}, usual range` (for a legend).
 */
export function normalBand({
  id,
  dates,
  mean,
  low,
  high,
  color,
  name,
  xAxisIndex = 0,
  yAxisIndex = 0,
}: {
  id: string
  dates: string[]
  mean: (number | null)[]
  low: (number | null)[]
  high: (number | null)[]
  color: string
  name: string
  xAxisIndex?: number
  yAxisIndex?: number
}): object[] {
  const length = dates.length
  const fit = (values: (number | null)[]) => Array.from({ length }, (_, i) => rounded(values[i] ?? null))
  const [lower, upper] = band({ id, lower: fit(low), upper: fit(high), color, xAxisIndex, yAxisIndex }) as [
    object,
    object,
  ]
  return [
    lower,
    { ...upper, name: bandName(name), itemStyle: { color, opacity: 0.35 } },
    {
      id: `${id}-mean`,
      name,
      type: 'line',
      xAxisIndex,
      yAxisIndex,
      data: fit(mean),
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 2, color, type: 'dashed' },
      itemStyle: { color },
    },
  ]
}

export const bandName = (name: string) => `${name}, usual range`

// --- This year against normal (`/climate/compare`) ------------------------------------------------------------

export type CompareTotal = { percentile: number | null; days_ahead?: number | null; missing_days?: number }

/** `/climate/compare`'s answer for one location, every day of the span kept (the normal runs past the forecast) */
export type CompareTable = {
  dates: string[]
  /** Each day's kind; null past the forecast's end (no value this year, the normal only) */
  kinds: (Kind | null)[]
  values: Record<string, (number | null)[]>
  /** Each numeric column's unit symbol (`in`, `degF_day`, `percent`) */
  units: Record<string, string>
  /** The last observed day, where the summary's percentiles are taken */
  asOf: string | null
  /** Per total (`precipitation_sum`, `dd_modified_50_86`): its percentile at `asOf`, days ahead (degree days) */
  totals: Record<string, CompareTotal>
  years: PeriodYears | null
  estimatedDays: number
  warnings: string[]
}

export function compareTable(body: Body): CompareTable {
  const data = columnsOf(body)
  const dates = (data.date ?? []) as string[]
  const kinds = ((data.kind ?? []) as (string | null)[]).map((kind) =>
    kind === 'observed' || kind === 'partial' || kind === 'forecast' ? (kind as Kind) : null,
  )
  const values: Record<string, (number | null)[]> = {}
  const units: Record<string, string> = {}
  for (const [name, column] of Object.entries(data)) {
    if (['date', 'day_of_year', 'kind', 'point'].includes(name)) continue
    values[name] = column.map((value) => (typeof value === 'number' ? value : null))
    const symbol = unitSymbol(body.meta.units[name] ?? '', name)
    if (symbol) units[name] = symbol
  }
  const summary = (body.meta.summary ?? {}) as Record<string, unknown>
  const compare = (Array.isArray(summary.compare) ? summary.compare[0] : summary.compare) as
    { as_of?: string | null; totals?: Record<string, CompareTotal> } | undefined
  return {
    dates,
    kinds,
    values,
    units,
    asOf: compare?.as_of ?? null,
    totals: compare?.totals ?? {},
    years: summaryYears(summary),
    estimatedDays: typeof summary.estimated_days === 'number' ? summary.estimated_days : 0,
    warnings: body.meta.warnings ?? [],
  }
}

/** A total's color: degree days green, precipitation blue, ET and sunlight gold, counts the high's */
export function measureColor(column: string, palette: Palette): string {
  if (column.startsWith('dd_')) return palette.degreeDays
  if (column.startsWith('precipitation')) return palette.precipitation
  if (column.startsWith('et0') || column.startsWith('shortwave')) return palette.et
  return palette.temperature.max
}

/** A column's values in the reader's units */
function displayed(table: CompareTable, units: Units, name: string): (number | null)[] {
  const values = table.values[name] ?? []
  const symbol = table.units[name]
  return values.map((value) => rounded(symbol ? units.toDisplay(symbol, value) : value))
}

function unitOf(table: CompareTable, units: Units, column: string): { label: string; digits: number } {
  const symbol = table.units[`${column}_cum`] ?? table.units[`${column}_cum_normal`]
  return symbol ? { label: units.label(symbol), digits: units.digits(symbol) } : { label: '', digits: 1 }
}

/** The span's year, from its first date */
const yearOf = (table: CompareTable) => Number((table.dates[0] ?? '').slice(0, 4))

/** The normal's name: "Normal (1996–2025)" */
export const normalName = (years: PeriodYears | null) => (years ? `Normal (${years.first}–${years.last})` : 'Normal')

/**
 * This year's running total of `column` (`precipitation_sum`, `dd_modified_50_86`, a count) from the span's start:
 * observed solid and on through the forecast's shading, over the normal (dashed) with its 10th–90th percentile band,
 * and, with `lastYear`, last year's total to the same date. `label` names what's totalled, over the axis.
 */
export function compareOption({
  table,
  column,
  units,
  palette,
  today,
  label,
  lastYear = true,
}: {
  table: CompareTable
  column: string
  units: Units
  palette: Palette
  today: string
  label: string
  lastYear?: boolean
}): EChartsCoreOption {
  const base = baseOption(palette)
  const { dates, kinds } = table
  const color = measureColor(column, palette)
  const unit = unitOf(table, units, column)
  const year = yearOf(table)
  const values = (suffix: string) => displayed(table, units, `${column}${suffix}`)
  const normal = normalName(table.years)
  const thisYear = String(year)
  const lastYearName = String(year - 1)

  const from = kinds.findIndex((kind) => kind === 'forecast' || kind === 'partial')
  const shading = forecastShading({ dates, from, grids: 1, axisOffset: 1, palette })
  // The shading ends with the forecast, not the year
  const shadingSeries = shading.series.map((s) => ({
    ...s,
    data: (s as { data: (number | null)[] }).data.map((v, i) => (kinds[i] ? v : null)),
  }))
  const last = kinds.findLastIndex((kind) => kind !== null)
  const forecastLabel =
    from >= 0 && last >= from
      ? {
          silent: true,
          itemStyle: { opacity: 0 },
          label: { show: true, position: 'insideTop', color: palette.inkMuted, fontSize: 10, formatter: 'Forecast' },
          data: [[{ xAxis: dates[from] }, { xAxis: dates[last] }]],
        }
      : undefined

  const series: object[] = [
    ...normalBand({
      id: 'normal',
      dates,
      mean: values('_cum_normal'),
      low: values('_cum_normal_p10'),
      high: values('_cum_normal_p90'),
      color: palette.normal,
      name: normal,
    }),
  ]
  if (lastYear && table.values[`${column}_cum_last_year`]?.some((v) => v !== null)) {
    series.push({
      id: 'last-year',
      name: lastYearName,
      type: 'line',
      data: values('_cum_last_year'),
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 1.5, color: palette.inkMuted },
      itemStyle: { color: palette.inkMuted },
    })
  }
  series.push({
    id: 'this-year',
    name: thisYear,
    type: 'line',
    data: values('_cum'),
    symbol: 'circle',
    showSymbol: false,
    symbolSize: 4,
    connectNulls: false,
    lineStyle: { width: 2.5, color },
    itemStyle: { color },
    markLine: { silent: true, symbol: 'none', data: todayLine(dates, today, palette) },
    markArea: forecastLabel,
  })

  const legendNames = series.map((s) => (s as { name: string }).name).filter((name) => !name.endsWith(' lower'))
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => rowLabel(date, undefined, { short: true }) }

  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: {
      type: 'scroll',
      top: 0,
      left: 0,
      right: 0,
      data: legendNames,
      textStyle: { color: palette.ink, fontSize: 11 },
      itemWidth: 14,
    },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number; seriesName: string }[]
        const index = list[0]?.dataIndex
        if (index === undefined) return ''
        return compareTooltip({ table, column, units, index, names: { normal, thisYear, lastYearName }, palette })
      },
    },
    grid: [{ left: 52, right: 16, top: 46, bottom: 24 }],
    xAxis: [{ type: 'category', data: dates, axisLabel, axisLine: base.axisLine }, ...shading.xAxis],
    yAxis: [
      {
        type: 'value',
        min: 0,
        name: unit.label ? `${label} (${unit.label})` : label,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        splitNumber: 4,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, ...shading.xAxisIndexes] }],
    series: [...series, ...shadingSeries],
  }
}

function compareTooltip({
  table,
  column,
  units,
  index,
  names,
  palette,
}: {
  table: CompareTable
  column: string
  units: Units
  index: number
  names: { normal: string; thisYear: string; lastYearName: string }
  palette: Palette
}): string {
  const at = (suffix: string) => displayed(table, units, `${column}${suffix}`)[index] ?? null
  const unit = unitOf(table, units, column)
  const text = (value: number | null) =>
    value === null ? 'None' : `${value.toFixed(unit.digits)}${unit.label ? ` ${unit.label}` : ''}`
  const swatch = (color: string) =>
    `<span style="display:inline-block;margin-right:4px;border-radius:9px;width:9px;height:9px;background:${color}"></span>`
  const rows: string[] = []
  const now = at('_cum')
  if (now !== null) {
    const percentile = table.values[`${column}_percentile`]?.[index]
    const rank = typeof percentile === 'number' ? ` (${ordinal(percentile)} percentile)` : ''
    rows.push(row(`${swatch(measureColor(column, palette))}${names.thisYear}`, `<strong>${text(now)}</strong>${rank}`))
  }
  const low = at('_cum_normal_p10')
  const high = at('_cum_normal_p90')
  const range = low !== null && high !== null ? `, usually ${text(low)} to ${text(high)}` : ''
  rows.push(row(`${swatch(palette.normal)}${names.normal}`, `${text(at('_cum_normal'))}${range}`))
  const before = at('_cum_last_year')
  if (before !== null) rows.push(row(`${swatch(palette.inkMuted)}${names.lastYearName}`, text(before)))
  const kind = table.kinds[index]
  const note = kind === 'forecast' ? ' (forecast)' : kind === 'partial' ? ' (today, partly forecast)' : ''
  return `<strong>${formatDate(table.dates[index], { weekday: true })}${note}</strong><table>${rows.join('')}</table>`
}

const row = (name: string, value: string) =>
  `<tr><td style="padding-right:12px">${name}</td><td style="text-align:right">${value}</td></tr>`

/**
 * The comparison in words, as of the last observed day: this year's total, where it ranks among the period's
 * years, its departure from normal and the usual range, days ahead or behind (degree days), last year's to the
 * same date, and any estimated days.
 */
export function compareSummary({
  table,
  column,
  units,
  label,
}: {
  table: CompareTable
  column: string
  units: Units
  label: string
}): string {
  const asOf = table.asOf
  const index = asOf ? table.dates.indexOf(asOf) : -1
  const unit = unitOf(table, units, column)
  const text = (value: number | null | undefined) =>
    value === null || value === undefined
      ? 'none'
      : `${value.toLocaleString('en-US', { minimumFractionDigits: unit.digits, maximumFractionDigits: unit.digits })}${unit.label ? ` ${unit.label}` : ''}`
  const at = (suffix: string) => (index >= 0 ? (displayed(table, units, `${column}${suffix}`)[index] ?? null) : null)
  const start = table.dates[0]
  const since = start ? `from ${formatDate(start)}` : ''
  const period = table.years ? periodWords(table.years) : "the period's years"
  if (index < 0 || at('_cum') === null) {
    const end = table.dates.at(-1)
    const normalEnd = end ? displayed(table, units, `${column}_cum_normal`).at(-1) : null
    return `No days ${since} have been observed yet. Over ${period}, the normal total by ${formatDate(end)} is ${text(normalEnd)}.`
  }
  const now = at('_cum')
  const normal = at('_cum_normal')
  const sentences = [`${label} ${since} through ${formatDate(asOf)}: ${text(now)}.`]
  const total = table.totals[column]
  const percentile = total?.percentile ?? null
  if (normal !== null && now !== null) {
    const departure = now - normal
    const direction =
      Math.abs(departure) < 10 ** -unit.digits / 2 ? 'the same as' : departure > 0 ? 'more than' : 'less than'
    const by = direction === 'the same as' ? '' : `${text(Math.abs(departure))} `
    sentences.push(`That is ${by}${direction} the normal of ${text(normal)} for the date.`)
  }
  if (percentile !== null) {
    sentences.push(`It ranks in the ${ordinal(percentile)} percentile of ${period}: ${percentileWords(percentile)}.`)
  }
  const low = at('_cum_normal_p10')
  const high = at('_cum_normal_p90')
  if (low !== null && high !== null) {
    sentences.push(`In 8 years out of 10, the total by this date was between ${text(low)} and ${text(high)}.`)
  }
  if (total && 'days_ahead' in total) {
    if (typeof total.days_ahead === 'number') sentences.push(`This year is ${daysAheadWords(total.days_ahead)}.`)
    else if (percentile !== null && percentile >= 50)
      sentences.push('The normal doesn’t reach this total until after the end of the year.')
  }
  const before = at('_cum_last_year')
  if (before !== null) sentences.push(`Last year by the same date: ${text(before)}.`)
  if (typeof total?.missing_days === 'number' && total.missing_days > 0)
    sentences.push(
      total.missing_days === 1
        ? '1 day has no value and is not counted.'
        : `${total.missing_days} days have no value and are not counted.`,
    )
  if (table.estimatedDays > 0 && !column.startsWith('precipitation'))
    sentences.push(
      `Includes ${table.estimatedDays} estimated day${table.estimatedDays === 1 ? '' : 's'} where a short gap in the data was bridged.`,
    )
  return sentences.join(' ')
}

/** "Summary and data"'s table: each day's total, the normal and its range, last year's */
export function compareRows(table: CompareTable, column: string, units: Units) {
  const unit = unitOf(table, units, column)
  const series = ['_cum', '_cum_normal', '_cum_normal_p10', '_cum_normal_p90', '_cum_last_year'].map((suffix) =>
    displayed(table, units, `${column}${suffix}`),
  )
  const year = yearOf(table)
  const suffix = unit.label ? ` (${unit.label})` : ''
  return {
    columns: [`${year}${suffix}`, `Normal${suffix}`, '10th percentile', '90th percentile', `${year - 1}${suffix}`],
    rows: table.dates
      .map((date, i) => ({
        date,
        forecast: table.kinds[i] === 'forecast' || table.kinds[i] === 'partial',
        values: series.map((values) => (values[i] === null ? null : values[i]!.toFixed(unit.digits))),
      }))
      .toReversed(),
  }
}

// --- Freezes (`/climate/frost/chances`, `/climate/frost`) ------------------------------------------------------

export type FreezeShow = 'spring' | 'fall' | 'both'

/** `/climate/frost/chances`'s long table, by threshold: each date's chance (percent) of a freeze at or below it,
 * after the date in spring (January–June), on or before it in fall (July–December) */
export type FreezeChances = {
  /** The thresholds' unit symbol (`degF`, `degC`) */
  unit: string
  thresholds: number[]
  dates: string[]
  season: ('spring' | 'fall')[]
  /** By threshold (as `String(threshold)`), one chance per date */
  chance: Record<string, (number | null)[]>
  years: PeriodYears | null
}

/** The unit thresholds are in: `meta.units.threshold`, else the request's `threshold_units`, else °F */
function thresholdUnit(body: Body): string {
  const label = body.meta.units.threshold ?? (body.meta.request.threshold_units as string | undefined) ?? '°F'
  return label === '°C' ? 'degC' : 'degF'
}

export function freezeChances(body: Body): FreezeChances {
  const data = columnsOf(body)
  const thresholds: number[] = []
  const dates: string[] = []
  const season: ('spring' | 'fall')[] = []
  const chance: Record<string, (number | null)[]> = {}
  const rows = (data.threshold ?? []).length
  for (let i = 0; i < rows; i++) {
    const threshold = data.threshold[i] as number
    const key = String(threshold)
    if (!(key in chance)) {
      thresholds.push(threshold)
      chance[key] = []
    }
    // The dates repeat per threshold: the first threshold's are the table's
    if (threshold === thresholds[0]) {
      dates.push(data.date[i] as string)
      season.push(data.season[i] === 'fall' ? 'fall' : 'spring')
    }
    const value = data.chance[i]
    chance[key].push(typeof value === 'number' ? value : null)
  }
  return {
    unit: thresholdUnit(body),
    thresholds,
    dates,
    season,
    chance,
    years: summaryYears(body.meta.summary as Record<string, unknown>),
  }
}

/** A threshold in °F (the names and the default thresholds are °F) */
const fahrenheit = (value: number, unit: string) => (unit === 'degC' ? Math.round((value * 9) / 5 + 32) : value)

/** Each threshold's dash, in order: lines are never told apart by color alone */
export const FREEZE_DASHES = ['solid', 'dashed', 'dotted'] as const
/** Each threshold's color token (for a table's key), as `freezeStyle` takes it from the palette */
export const FREEZE_TOKENS = [
  '--color-chart-temperature-min',
  '--color-chart-projection',
  '--color-chart-temperature-max',
] as const

/** The k-th threshold's color and dash */
export function freezeStyle(k: number, palette: Palette) {
  const colors = [palette.temperature.min, palette.projection, palette.temperature.max]
  return { color: colors[k % colors.length], type: FREEZE_DASHES[k % FREEZE_DASHES.length] }
}

/** The days worth drawing: from a week before any chance leaves 100% (spring) or 0% (fall) to a week after the
 * last change, for the seasons shown */
function freezeSpan(chances: FreezeChances, shown: number[], show: FreezeShow): [number, number] {
  const n = chances.dates.length
  const inSeason = (i: number) => show === 'both' || chances.season[i] === show
  let first = -1
  let last = -1
  for (const threshold of shown) {
    const values = chances.chance[String(threshold)] ?? []
    for (let i = 0; i < n; i++) {
      if (!inSeason(i)) continue
      const v = values[i]
      if (v === null || v <= 0 || v >= 100) continue
      if (first < 0 || i < first) first = i
      if (i > last) last = i
    }
  }
  if (first < 0) {
    const indexes = chances.dates.map((_, i) => i).filter(inSeason)
    return [indexes[0] ?? 0, indexes.at(-1) ?? n - 1]
  }
  const lo = Math.max(0, first - 7)
  const hi = Math.min(n - 1, last + 7)
  return [lo, hi]
}

/**
 * The chance of a freeze by date, a line per threshold (`thresholds`, in the chances' unit; default all): in spring
 * the chance one still comes after the date, in fall the chance one has come by it. Dashed lines mark 10%, 50% and
 * 90%, which the dates table reads across; Today is marked.
 */
export function freezeOddsOption({
  chances,
  thresholds,
  show = 'both',
  today,
  units,
  palette,
}: {
  chances: FreezeChances
  thresholds?: number[]
  show?: FreezeShow
  today: string
  units: Units
  palette: Palette
}): EChartsCoreOption {
  const base = baseOption(palette)
  const shown = (thresholds ?? chances.thresholds).filter((t) => String(t) in chances.chance)
  const [lo, hi] = freezeSpan(chances, shown, show)
  const dates = chances.dates.slice(lo, hi + 1)
  const names = shown.map((t) => thresholdLabel(fahrenheit(t, chances.unit), units))
  const marks = [...todayLine(dates, today, palette), ...[10, 50, 90].map((p) => thresholdLine(p, `${p}%`, palette))]
  const series = shown.map((threshold, k) => {
    const style = freezeStyle(k, palette)
    const values = (chances.chance[String(threshold)] ?? []).slice(lo, hi + 1)
    return {
      id: `freeze-${threshold}`,
      name: names[k],
      type: 'line',
      data: values,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 2, color: style.color, type: style.type },
      itemStyle: { color: style.color },
      ...(k === 0 ? { markLine: { silent: true, symbol: 'none', data: marks } } : {}),
    }
  })
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => formatDate(date) }
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: {
      type: 'scroll',
      top: 0,
      left: 0,
      right: 0,
      data: names,
      textStyle: { color: palette.ink, fontSize: 11 },
      itemWidth: 22,
    },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as {
          dataIndex: number
          seriesName: string
          marker: string
          value: unknown
        }[]
        if (!list.length) return ''
        const index = list[0].dataIndex
        const spring = chances.season[lo + index] === 'spring'
        const rows = list.map((p) =>
          row(
            `${p.marker}${p.seriesName}`,
            typeof p.value === 'number' ? `<strong>${Math.round(p.value)}%</strong>` : 'None',
          ),
        )
        const heading = spring ? 'Chance of a freeze after' : 'Chance of a freeze by'
        return `<strong>${heading} ${formatDate(dates[index])}</strong><table>${rows.join('')}</table>`
      },
    },
    grid: [{ left: 44, right: 16, top: 46, bottom: 24 }],
    xAxis: [{ type: 'category', data: dates, axisLabel, axisLine: base.axisLine }],
    yAxis: [
      {
        type: 'value',
        min: 0,
        max: 100,
        interval: 25,
        name: 'Chance (%)',
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0] }],
    series,
  }
}

/** "Summary and data"'s table for the odds: each date's chance per threshold */
export function freezeOddsRows(chances: FreezeChances, units: Units, thresholds?: number[], show: FreezeShow = 'both') {
  const shown = (thresholds ?? chances.thresholds).filter((t) => String(t) in chances.chance)
  return {
    columns: shown.map((t) => `${thresholdLabel(fahrenheit(t, chances.unit), units)} (%)`),
    rows: chances.dates
      .map((date, i) => ({
        date,
        forecast: false,
        values: shown.map((t) => {
          const v = chances.chance[String(t)]?.[i]
          return v === null || v === undefined ? null : String(Math.round(v))
        }),
      }))
      .filter((_, i) => show === 'both' || chances.season[i] === show),
  }
}

/** One threshold's freeze dates from `/climate/frost`: each probability's date (this year's) or null */
export type FreezeRow = {
  /** As the answer gives it, in `FreezeDates.unit` */
  threshold: number
  /** °F, for naming */
  fahrenheit: number
  /** By probability (10, 50, 90): the date by which that share of years had had their last spring freeze */
  lastSpring: Record<number, string | null>
  /** By probability: the date by which that share had had their first fall freeze */
  firstFall: Record<number, string | null>
  /** By probability: the frost-free season's length that share of years were at or under, days */
  seasonDays: Record<number, number | null>
  yearsSpring: number
  yearsFall: number
  withoutSpring: number
  withoutFall: number
}

export type FreezeDates = { unit: string; rows: FreezeRow[]; probabilities: number[]; years: PeriodYears | null }

export function freezeDates(body: Body): FreezeDates {
  const data = columnsOf(body)
  const unit = thresholdUnit(body)
  const probabilities = Object.keys(data)
    .map((name) => /^last_spring_p(\d+(?:p\d+)?)$/.exec(name)?.[1])
    .filter((p): p is string => !!p)
    .map((p) => Number(p.replace('p', '.')))
    .sort((a, b) => a - b)
  const suffix = (p: number) => `p${String(p).replace('.', 'p')}`
  const number = (value: unknown) => (typeof value === 'number' ? value : 0)
  const rows = ((data.threshold ?? []) as number[]).map((threshold, i): FreezeRow => {
    const by = <T>(name: string) =>
      Object.fromEntries(probabilities.map((p) => [p, (data[`${name}_${suffix(p)}`]?.[i] ?? null) as T | null]))
    return {
      threshold,
      fahrenheit: fahrenheit(threshold, unit),
      lastSpring: by<string>('last_spring'),
      firstFall: by<string>('first_fall'),
      seasonDays: by<number>('season_days'),
      yearsSpring: number(data.years_spring?.[i]),
      yearsFall: number(data.years_fall?.[i]),
      withoutSpring: number(data.years_without_spring?.[i]),
      withoutFall: number(data.years_without_fall?.[i]),
    }
  })
  return { unit, rows, probabilities, years: summaryYears(body.meta.summary as Record<string, unknown>) }
}

/**
 * The freeze dates in words, a sentence or two per threshold: in spring, the date by which half the years had
 * had their last freeze and how late 1 year in 10 ran; in fall, the date of the first in half the years and how
 * early 1 year in 10 came; with both, the frost-free season's typical length.
 */
export function freezeSummary({
  dates,
  units,
  show = 'both',
}: {
  dates: FreezeDates
  units: Units
  show?: FreezeShow
}): string {
  const period = dates.years ? periodWords(dates.years) : "the period's years"
  const sentences = [`Over ${period}:`]
  const has = (p: number) => dates.probabilities.includes(p)
  for (const row of dates.rows) {
    const noun = thresholdNoun(row.fahrenheit, units)
    const label = thresholdLabel(row.fahrenheit, units)
    if (show !== 'fall') {
      if (row.withoutSpring === row.yearsSpring && row.yearsSpring > 0) {
        sentences.push(`No year had a spring ${noun}.`)
      } else if (has(50)) {
        const median = row.lastSpring[50]
        const late = has(90) ? row.lastSpring[90] : null
        sentences.push(
          `${label}: the last of spring came by ${formatDate(median)} in ${shareOfYears(50)}${late ? `, and after ${formatDate(late)} in ${shareOfYears(10)}` : ''}.`,
        )
      }
    }
    if (show !== 'spring') {
      if (row.withoutFall === row.yearsFall && row.yearsFall > 0) {
        sentences.push(`No year had a fall ${noun}.`)
      } else if (has(50)) {
        const median = row.firstFall[50]
        const early = has(10) ? row.firstFall[10] : null
        const lead = show === 'fall' ? `${label}: the first` : 'The first'
        sentences.push(
          `${lead} of fall came by ${formatDate(median)} in ${shareOfYears(50)}${early ? `, and by ${formatDate(early)} in ${shareOfYears(10)}` : ''}.`,
        )
      }
    }
    if (show === 'both' && has(50) && row.seasonDays[50] !== null) {
      const low = has(10) ? row.seasonDays[10] : null
      const high = has(90) ? row.seasonDays[90] : null
      const range = low !== null && high !== null ? ` (${low} to ${high} days in 8 years out of 10)` : ''
      sentences.push(`The season without a ${noun} typically lasted ${row.seasonDays[50]} days${range}.`)
    }
  }
  return sentences.join(' ')
}

/** A year's own freeze dates from `/freeze`, by threshold in °F: its last spring freeze and first fall freeze, or
 * null where it had none (yet) */
export function yearFreezes(body: Body): Map<number, { spring: string | null; fall: string | null }> {
  const data = columnsOf(body)
  const unit = thresholdUnit(body)
  const found = new Map<number, { spring: string | null; fall: string | null }>()
  ;((data.threshold ?? []) as number[]).forEach((threshold, i) =>
    found.set(fahrenheit(threshold, unit), {
      spring: (data.last_spring?.[i] as string | null) ?? null,
      fall: (data.first_fall?.[i] as string | null) ?? null,
    }),
  )
  return found
}
