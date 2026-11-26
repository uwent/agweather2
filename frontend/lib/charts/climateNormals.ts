// The Climate tab's normals charts (Phase 7 track 6.2), beside climateCharts.ts's comparisons and freeze odds:
// recent highs and lows against their normals, and one variable's normal through the year. Pure builders over the
// API's column names, so `/climate`'s explorer draws them alike.
//
//   const recent = recentNormal(weatherBody, [normalsBody])   // `/weather/daily` beside `/climate/normals`
//   recentNormalOption({ recent, units, palette, today })
//   recentNormalSummary({ recent, units })
//   const normal = normalYear(body, 'precipitation_sum')       // `/climate/normals` with `percentiles=10,90`
//   normalYearOption({ normal, units, palette, today, label, color })
//   normalYearSummary({ normal, units, today, label })
//
// Values stay in the units the answer gives (pages ask with `units=us`) and are converted at display.

import type { TableResponse } from '@/types/api'

import { periodWords, summaryYears, type PeriodYears } from '../climate/periods'
import { formatDate } from '../dates'
import { unitSymbol, type Kind } from '../tableRows'
import type { Units } from '../units'
import { bandName, normalBand, normalName } from './climateCharts'
import type { EChartsCoreOption } from './echarts'
import { rowLabel, todayLine } from './kinds'
import { baseOption, type Palette } from './palette'
import { forecastShading } from './shading'

type Body = Pick<TableResponse, 'meta' | 'data'>
type Columns = Record<string, (number | string | boolean | null)[]>

const columnsOf = (body: Body): Columns => (Array.isArray(body.data) ? {} : (body.data as Columns))
const rounded = (value: number | null) => (value === null ? null : Number(value.toFixed(3)))
const numberOrNull = (value: unknown) => (typeof value === 'number' ? value : null)
const row = (name: string, value: string) =>
  `<tr><td style="padding-right:12px">${name}</td><td style="text-align:right">${value}</td></tr>`
const swatch = (color: string) =>
  `<span style="display:inline-block;margin-right:4px;border-radius:9px;width:9px;height:9px;background:${color}"></span>`

function legend(names: string[], palette: Palette) {
  return {
    type: 'scroll',
    top: 0,
    left: 0,
    right: 0,
    data: names,
    textStyle: { color: palette.ink, fontSize: 11 },
    itemWidth: 14,
  }
}

// --- Recent temperatures against normal ------------------------------------------------------------------------

/** The last weeks' highs and lows through the forecast, beside each day's normal and its 10th–90th percentiles;
 * all °F, as asked with `units=us` */
export type RecentNormal = {
  dates: string[]
  kinds: Kind[]
  highs: (number | null)[]
  lows: (number | null)[]
  normal: {
    max: (number | null)[]
    maxLow: (number | null)[]
    maxHigh: (number | null)[]
    min: (number | null)[]
    minLow: (number | null)[]
    minHigh: (number | null)[]
  }
  years: PeriodYears | null
  warnings: string[]
}

/**
 * `/weather/daily`'s highs and lows (days past the forecast left out) beside `/climate/normals`' for the same days,
 * given as one answer or two (a span across January 1 asks each year's days apart, as normals keep to one year)
 */
export function recentNormal(weather: Body, normals: Body[]): RecentNormal {
  const data = columnsOf(weather)
  const byDate = new Map<string, Record<string, number | null>>()
  let years: PeriodYears | null = null
  const warnings = [...(weather.meta.warnings ?? [])]
  for (const body of normals) {
    const columns = columnsOf(body)
    ;((columns.date ?? []) as string[]).forEach((date, i) => {
      byDate.set(date, Object.fromEntries(Object.entries(columns).map(([name, col]) => [name, numberOrNull(col[i])])))
    })
    years ??= summaryYears(body.meta.summary as Record<string, unknown>)
    warnings.push(...(body.meta.warnings ?? []))
  }
  const rows: { date: string; kind: Kind; high: number | null; low: number | null }[] = []
  ;((data.date ?? []) as string[]).forEach((date, i) => {
    const kind = data.kind?.[i]
    if (kind !== 'observed' && kind !== 'partial' && kind !== 'forecast') return
    rows.push({
      date,
      kind,
      high: numberOrNull(data.air_temperature_max?.[i]),
      low: numberOrNull(data.air_temperature_min?.[i]),
    })
  })
  const normal = (name: string) => rows.map((r) => byDate.get(r.date)?.[name] ?? null)
  return {
    dates: rows.map((r) => r.date),
    kinds: rows.map((r) => r.kind),
    highs: rows.map((r) => r.high),
    lows: rows.map((r) => r.low),
    normal: {
      max: normal('air_temperature_max'),
      maxLow: normal('air_temperature_max_p10'),
      maxHigh: normal('air_temperature_max_p90'),
      min: normal('air_temperature_min'),
      minLow: normal('air_temperature_min_p10'),
      minHigh: normal('air_temperature_min_p90'),
    },
    years,
    warnings: [...new Set(warnings)],
  }
}

/** The requests a span from `start` to `end` (ISO) takes of `/climate/normals`: one per calendar year */
export function normalSpans(start: string, end: string): { start: string; end: string }[] {
  const spans: { start: string; end: string }[] = []
  let from = start
  while (from <= end) {
    const yearEnd = `${from.slice(0, 4)}-12-31`
    spans.push({ start: from, end: yearEnd < end ? yearEnd : end })
    from = `${Number(from.slice(0, 4)) + 1}-01-01`
  }
  return spans
}

const temperatures = (units: Units, values: (number | null)[]) =>
  values.map((value) => rounded(units.toDisplay('degF', value)))

/** The highs (red) and lows (blue) as lines over their normals, each dashed over its usual range; the forecast
 * shaded, Today marked */
export function recentNormalOption({
  recent,
  units,
  palette,
  today,
}: {
  recent: RecentNormal
  units: Units
  palette: Palette
  today: string
}): EChartsCoreOption {
  const base = baseOption(palette)
  const { dates, kinds } = recent
  const names = recentNames(recent)
  const from = kinds.findIndex((kind) => kind === 'forecast' || kind === 'partial')
  const shading = forecastShading({ dates, from, grids: 1, axisOffset: 1, palette })
  const forecastLabel =
    from >= 0
      ? {
          silent: true,
          itemStyle: { opacity: 0 },
          label: { show: true, position: 'insideTop', color: palette.inkMuted, fontSize: 10, formatter: 'Forecast' },
          data: [[{ xAxis: dates[from] }, { xAxis: dates[dates.length - 1] }]],
        }
      : undefined
  const line = (id: string, name: string, data: (number | null)[], color: string, extra: object = {}) => ({
    id,
    name,
    type: 'line',
    data,
    symbol: 'circle',
    showSymbol: false,
    symbolSize: 4,
    connectNulls: false,
    lineStyle: { width: 2, color },
    itemStyle: { color },
    ...extra,
  })
  const series: object[] = [
    ...normalBand({
      id: 'normal-high',
      dates,
      mean: temperatures(units, recent.normal.max),
      low: temperatures(units, recent.normal.maxLow),
      high: temperatures(units, recent.normal.maxHigh),
      color: palette.temperature.max,
      name: names.normalHigh,
    }),
    ...normalBand({
      id: 'normal-low',
      dates,
      mean: temperatures(units, recent.normal.min),
      low: temperatures(units, recent.normal.minLow),
      high: temperatures(units, recent.normal.minHigh),
      color: palette.temperature.min,
      name: names.normalLow,
    }),
    line('high', names.high, temperatures(units, recent.highs), palette.temperature.max, {
      markLine: { silent: true, symbol: 'none', data: todayLine(dates, today, palette) },
      markArea: forecastLabel,
    }),
    line('low', names.low, temperatures(units, recent.lows), palette.temperature.min),
  ]
  const legendNames = series.map((s) => (s as { name: string }).name).filter((name) => !name.endsWith(' lower'))
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => rowLabel(date, undefined, { short: true }) }
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: legend(legendNames, palette),
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        const index = list[0]?.dataIndex
        return index === undefined ? '' : recentTooltip({ recent, units, index, palette })
      },
    },
    grid: [{ left: 44, right: 16, top: 46, bottom: 24 }],
    xAxis: [{ type: 'category', data: dates, axisLabel, axisLine: base.axisLine }, ...shading.xAxis],
    yAxis: [
      {
        type: 'value',
        scale: true,
        name: `Temperature (${units.label('degF')})`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        splitNumber: 4,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, ...shading.xAxisIndexes] }],
    series: [...series, ...shading.series],
  }
}

function recentNames(recent: RecentNormal) {
  const span = recent.years ? ` (${recent.years.first}–${recent.years.last})` : ''
  return { high: 'High', low: 'Low', normalHigh: `Normal high${span}`, normalLow: `Normal low${span}` }
}

function recentTooltip({
  recent,
  units,
  index,
  palette,
}: {
  recent: RecentNormal
  units: Units
  index: number
  palette: Palette
}): string {
  const names = recentNames(recent)
  const text = (value: number | null) => units.format('degF', value)
  const range = (low: number | null, high: number | null) =>
    low !== null && high !== null ? `, usually ${text(low)} to ${text(high)}` : ''
  const { normal } = recent
  const rows = [
    row(`${swatch(palette.temperature.max)}${names.high}`, `<strong>${text(recent.highs[index])}</strong>`),
    row(names.normalHigh, `${text(normal.max[index])}${range(normal.maxLow[index], normal.maxHigh[index])}`),
    row(`${swatch(palette.temperature.min)}${names.low}`, `<strong>${text(recent.lows[index])}</strong>`),
    row(names.normalLow, `${text(normal.min[index])}${range(normal.minLow[index], normal.minHigh[index])}`),
  ]
  const kind = recent.kinds[index]
  const note = kind === 'forecast' ? ' (forecast)' : kind === 'partial' ? ' (today, partly forecast)' : ''
  return `<strong>${formatDate(recent.dates[index], { weekday: true })}${note}</strong><table>${rows.join('')}</table>`
}

/** The mean of the days' departures from normal (°F), over the days that have both */
function meanDeparture(values: (number | null)[], normal: (number | null)[], indexes: number[]): number | null {
  const found = indexes.flatMap((i) => {
    const value = values[i]
    const usual = normal[i]
    return value !== null && value !== undefined && usual !== null && usual !== undefined ? [value - usual] : []
  })
  return found.length ? found.reduce((a, b) => a + b, 0) / found.length : null
}

/** A departure in °F in words: "4 °F above normal", or "about normal" within half a degree in the reader's units */
export function departureWords(departureF: number, units: Units): string {
  const shown = units.toDisplay('delta_degF', departureF) ?? 0
  if (Math.abs(shown) < 0.5) return 'about normal'
  return `${units.format('delta_degF', Math.abs(departureF), { digits: 0 })} ${departureF > 0 ? 'above' : 'below'} normal`
}

/** The chart in words: how far highs and lows ran from normal over the last 7 and 30 observed days and in the
 * forecast, and how many observed days fell outside the usual range */
export function recentNormalSummary({ recent, units }: { recent: RecentNormal; units: Units }): string {
  const observed = recent.kinds.flatMap((kind, i) => (kind === 'observed' ? [i] : []))
  const ahead = recent.kinds.flatMap((kind, i) => (kind === 'forecast' ? [i] : []))
  const { normal } = recent
  const sentences: string[] = []
  const describe = (indexes: number[], lead: string) => {
    const high = meanDeparture(recent.highs, normal.max, indexes)
    const low = meanDeparture(recent.lows, normal.min, indexes)
    if (high === null || low === null) return
    sentences.push(`${lead}, highs averaged ${departureWords(high, units)} and lows ${departureWords(low, units)}.`)
  }
  const week = observed.slice(-7)
  if (week.length) {
    const span = `${formatDate(recent.dates[week[0]])} to ${formatDate(recent.dates[week[week.length - 1]])}`
    describe(week, `Over the last ${week.length} days (${span})`)
  }
  const month = observed.slice(-30)
  if (month.length > week.length) describe(month, `Over the last ${month.length} days`)
  if (ahead.length) describe(ahead, `In the forecast through ${formatDate(recent.dates[ahead[ahead.length - 1]])}`)
  const outside = (values: (number | null)[], limits: (number | null)[], beyond: (a: number, b: number) => boolean) =>
    observed.filter((i) => {
      const value = values[i]
      const limit = limits[i]
      return value !== null && limit !== null && beyond(value, limit)
    }).length
  if (observed.length) {
    const above = outside(recent.highs, normal.maxHigh, (a, b) => a > b)
    const below = outside(recent.lows, normal.minLow, (a, b) => a < b)
    sentences.push(
      `Of the ${observed.length} observed days shown, ${above} had a high above its usual range and ${below} had a low below its usual range; each happens about 1 year in 10.`,
    )
  }
  return sentences.length ? sentences.join(' ') : 'No observed days to compare yet.'
}

/** "Summary and data"'s table: each day's high and low beside their normals */
export function recentNormalRows(recent: RecentNormal, units: Units) {
  const unit = units.label('degF')
  const series = [recent.highs, recent.normal.max, recent.lows, recent.normal.min].map((values) =>
    values.map((value) => (value === null ? null : units.format('degF', value, { unit: false }))),
  )
  return {
    columns: [`High (${unit})`, `Normal high (${unit})`, `Low (${unit})`, `Normal low (${unit})`],
    rows: recent.dates
      .map((date, i) => ({
        date,
        forecast: recent.kinds[i] === 'forecast' || recent.kinds[i] === 'partial',
        values: series.map((values) => values[i]),
      }))
      .toReversed(),
  }
}

// --- A normal through the year ---------------------------------------------------------------------------------

/** One variable's daily normal over a calendar year with its 10th–90th percentiles; a variable that adds up
 * (precipitation, ET0, sunlight) as its running total from January 1 */
export type NormalYear = {
  variable: string
  dates: string[]
  mean: (number | null)[]
  low: (number | null)[]
  high: (number | null)[]
  /** The values' unit symbol (`degF`, `in`), as the answer gives it; empty for none */
  unit: string
  cumulative: boolean
  years: PeriodYears | null
}

/** `/climate/normals` for `variable` with `percentiles=10,90`: its running totals (`_cum`) if the answer has them,
 * else its daily values */
export function normalYear(body: Body, variable: string): NormalYear {
  const data = columnsOf(body)
  const cumulative = `${variable}_cum` in data
  const stem = cumulative ? `${variable}_cum` : variable
  const numbers = (name: string) => (data[name] ?? []).map(numberOrNull)
  return {
    variable,
    dates: (data.date ?? []) as string[],
    mean: numbers(stem),
    low: numbers(`${stem}_p10`),
    high: numbers(`${stem}_p90`),
    unit: unitSymbol(body.meta.units[stem] ?? '', stem) ?? '',
    cumulative,
    years: summaryYears(body.meta.summary as Record<string, unknown>),
  }
}

const shownIn = (normal: NormalYear, units: Units, values: (number | null)[]) =>
  values.map((value) => rounded(normal.unit ? units.toDisplay(normal.unit, value) : value))

function textIn(normal: NormalYear, units: Units) {
  const unit = normal.unit ? units.label(normal.unit) : ''
  const digits = normal.unit ? units.digits(normal.unit) : 1
  return (value: number | null | undefined) =>
    value === null || value === undefined
      ? 'none'
      : `${value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits })}${unit ? ` ${unit}` : ''}`
}

/** The normal over its usual range across the year, Today marked; `label` names it over the axis */
export function normalYearOption({
  normal,
  units,
  palette,
  today,
  label,
  color,
}: {
  normal: NormalYear
  units: Units
  palette: Palette
  today: string
  label: string
  color: string
}): EChartsCoreOption {
  const base = baseOption(palette)
  const { dates } = normal
  const name = normalName(normal.years)
  const unit = normal.unit ? units.label(normal.unit) : ''
  const text = textIn(normal, units)
  // Today's month and day in the normal's year
  const marks = todayLine(dates, `${dates[0]?.slice(0, 4) ?? ''}${today.slice(4)}`, palette)
  const [lower, upper, mean] = normalBand({
    id: 'normal',
    dates,
    mean: shownIn(normal, units, normal.mean),
    low: shownIn(normal, units, normal.low),
    high: shownIn(normal, units, normal.high),
    color,
    name,
  }) as [object, object, Record<string, unknown>]
  // With nothing else drawn, the normal is the chart's solid line
  const line = {
    ...mean,
    lineStyle: { width: 2, color, type: 'solid' },
    markLine: { silent: true, symbol: 'none', data: marks },
  }
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => formatDate(date) }
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: legend([name, bandName(name)], palette),
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        const index = list[0]?.dataIndex
        if (index === undefined) return ''
        const at = (values: (number | null)[]) => shownIn(normal, units, values)[index] ?? null
        const low = at(normal.low)
        const high = at(normal.high)
        const range = low !== null && high !== null ? `, usually ${text(low)} to ${text(high)}` : ''
        return `<strong>${formatDate(dates[index])}</strong><table>${row(name, `<strong>${text(at(normal.mean))}</strong>${range}`)}</table>`
      },
    },
    grid: [{ left: 52, right: 16, top: 46, bottom: 24 }],
    xAxis: [{ type: 'category', data: dates, axisLabel, axisLine: base.axisLine }],
    yAxis: [
      {
        type: 'value',
        scale: !normal.cumulative,
        min: normal.cumulative ? 0 : undefined,
        name: unit ? `${label} (${unit})` : label,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        splitNumber: 4,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0] }],
    series: [lower, upper, line],
  }
}

/** The normal through the year in words: on today's date with its usual range, and for a total the year's, for a
 * daily value its highest and lowest */
export function normalYearSummary({
  normal,
  units,
  today,
  label,
}: {
  normal: NormalYear
  units: Units
  today: string
  label: string
}): string {
  const values = shownIn(normal, units, normal.mean)
  const lows = shownIn(normal, units, normal.low)
  const highs = shownIn(normal, units, normal.high)
  const text = textIn(normal, units)
  const period = normal.years ? periodWords(normal.years) : 'the period’s years'
  const range = (i: number) =>
    lows[i] !== null && highs[i] !== null
      ? `, and between ${text(lows[i])} and ${text(highs[i])} in 8 years out of 10`
      : ''
  const sentences = [`${label}: the normal over ${period}.`]
  const index = normal.dates.findIndex((date) => date.slice(5) === today.slice(5))
  if (normal.cumulative) {
    if (index >= 0)
      sentences.push(
        `The normal total from January 1 to ${formatDate(normal.dates[index])} is ${text(values[index])}${range(index)}.`,
      )
    const last = values.length - 1
    if (last >= 0) sentences.push(`To ${formatDate(normal.dates[last])}, it is ${text(values[last])}${range(last)}.`)
  } else {
    if (index >= 0)
      sentences.push(`On ${formatDate(normal.dates[index])}, the normal is ${text(values[index])}${range(index)}.`)
    const known = values.flatMap((v, i) => (v === null ? [] : [i]))
    if (known.length) {
      const top = known.reduce((a, b) => ((values[b] as number) > (values[a] as number) ? b : a))
      const bottom = known.reduce((a, b) => ((values[b] as number) < (values[a] as number) ? b : a))
      sentences.push(
        `It is highest around ${formatDate(normal.dates[top])}, at ${text(values[top])}, and lowest around ${formatDate(normal.dates[bottom])}, at ${text(values[bottom])}.`,
      )
    }
  }
  return sentences.join(' ')
}

/** "Summary and data"'s table for a normal through the year */
export function normalYearRows(normal: NormalYear, units: Units) {
  const unit = normal.unit ? units.label(normal.unit) : ''
  const digits = normal.unit ? units.digits(normal.unit) : 1
  const suffix = unit ? ` (${unit})` : ''
  const series = [normal.mean, normal.low, normal.high].map((values) => shownIn(normal, units, values))
  return {
    columns: [`Normal${suffix}`, '10th percentile', '90th percentile'],
    rows: normal.dates.map((date, i) => ({
      date,
      forecast: false,
      values: series.map((values) => (values[i] === null ? null : values[i]!.toFixed(digits))),
    })),
  }
}

// --- The normals by month --------------------------------------------------------------------------------------

export type MonthlyNormals = {
  /** `2026-01` … `2026-12` */
  months: string[]
  /** By variable, its normal per month: a monthly mean (temperatures) or total (precipitation, ET0, sunlight) */
  values: Record<string, (number | null)[]>
  units: Record<string, string>
  years: PeriodYears | null
}

/** `/climate/normals?interval=month` */
export function monthlyNormals(body: Body): MonthlyNormals {
  const data = columnsOf(body)
  const values: Record<string, (number | null)[]> = {}
  const units: Record<string, string> = {}
  for (const [name, column] of Object.entries(data)) {
    if (name === 'month' || name === 'point') continue
    values[name] = column.map(numberOrNull)
    const symbol = unitSymbol(body.meta.units[name] ?? '', name)
    if (symbol) units[name] = symbol
  }
  return {
    months: (data.month ?? []) as string[],
    values,
    units,
    years: summaryYears(body.meta.summary as Record<string, unknown>),
  }
}

/** A year's figure from its months: a total's sum, else the months' mean weighted by their days; null if a month
 * is missing */
export function yearFromMonths(months: string[], values: (number | null)[], total: boolean): number | null {
  if (!values.length || values.some((v) => v === null)) return null
  if (total) return (values as number[]).reduce((a, b) => a + b, 0)
  const days = months.map((month) => {
    const [y, m] = month.split('-').map(Number)
    return new Date(Date.UTC(y, m, 0)).getUTCDate()
  })
  const all = days.reduce((a, b) => a + b, 0)
  return (values as number[]).reduce((sum, v, i) => sum + v * days[i], 0) / all
}
