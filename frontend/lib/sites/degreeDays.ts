// A site's Degree days tab (track 3 step 7; frontend.md, Tools: the degree-day calculator): up to three settings
// compared, each a preset from `/degree-days/presets` (a crop's usual setting or an insect model's, with its sources)
// or the reader's own method, base and upper; counted from January 1, a planting date or a biofix; `/degree-days`'
// daily values and running totals charted as two stacked grids on one time axis (daily bars, running totals as
// lines), estimated days hollow, and this year's projection to December 31 (D63) as its P50 dashed over the
// P10–P90 band. Settings travel in the page's view as text: a preset's id or a setting (`sine_41_86`, in °F).
//
//   const series = resolveSeries(['corn', 'sine_41_86'], presets)
//   get('/degree-days', ddQuery({ series, from: 'planting', date: '2026-05-10', year: 2026, thisYear: 2026 }))
//   const run = ddRun(body, series)
//   build = (palette) => ddOption({ run, units, palette, today })
//   ddWords({ run, units, from, date })   // the chart in words: its text alternative and summary

import type { PresetInfo, TableResponse } from '@/types/api'

import type { CsvValue } from '../csv'
import { formatDate } from '../dates'
import { routes } from '../routes'
import { band, bar, forecastBand, isForecast, lineStyle, point, rowLabel, todayLine } from '../charts/kinds'
import type { EChartsCoreOption } from '../charts/echarts'
import { baseOption, type Palette } from '../charts/palette'
import { tableRows, type Day, type Table } from '../tableRows'
import type { Units } from '../units'

export const MAX_SETTINGS = 3
/** The unit the tab asks for (`units=us`): settings and presets are named in °F, and values convert at display */
export const DD_UNIT = 'degF_day'

export type Method = 'sine' | 'modified' | 'average'
export const METHODS: { value: Method; label: string; description: string }[] = [
  {
    value: 'sine',
    label: 'Single sine',
    description: 'Fits a sine curve through the day’s low and high; the most common method for insects.',
  },
  {
    value: 'modified',
    label: 'Modified average',
    description: 'Raises the low to the base and lowers the high to the upper threshold, then averages them.',
  },
  { value: 'average', label: 'Simple average', description: 'The day’s average temperature less the base.' },
]

/** A degree-day setting, in °F */
export type Setting = { method: Method; base: number; upper: number | null }

/** One compared series: a preset, or the reader's own setting */
export type Series = {
  /** As kept in the view: the preset's id, or the setting's text */
  token: string
  /** `dd=` text in °F, as the API names the columns back (`dd_<dd>`, `dd_<dd>_cum`) */
  dd: string
  setting: Setting
  preset: PresetInfo | null
}

export type CountFrom = 'jan1' | 'planting' | 'biofix'

const SETTING = /^(sine|modified|average)_(\d+(?:p\d+)?)(?:_(\d+(?:p\d+)?))?$/

const number = (text: string) => Number(text.replace('p', '.'))
const numberText = (value: number) => `${Number(value.toFixed(1))}`.replace('.', 'p')

/** `sine_41_86` for single sine above 41 °F with an upper threshold of 86 °F; tenths of a degree as `39p2` */
export function settingText(setting: Setting): string {
  const upper = setting.upper === null ? '' : `_${numberText(setting.upper)}`
  return `${setting.method}_${numberText(setting.base)}${upper}`
}

export function parseSetting(text: string): Setting | null {
  const match = SETTING.exec(text)
  if (!match) return null
  return { method: match[1] as Method, base: number(match[2]), upper: match[3] ? number(match[3]) : null }
}

/** The settings in the view (`corn;sine_41_86`), at most three, each once */
export function decodeTokens(text: string | null | undefined): string[] {
  const tokens = (text ?? '').split(';').filter(Boolean)
  return [...new Set(tokens)].slice(0, MAX_SETTINGS)
}

export const encodeTokens = (tokens: string[]): string => tokens.join(';')

/** The tokens as series, dropping any that name no preset and aren't a setting */
export function resolveSeries(tokens: string[], presets: PresetInfo[]): Series[] {
  const found: Series[] = []
  for (const token of tokens) {
    const preset = presets.find((p) => p.id === token) ?? null
    const setting = preset
      ? { method: preset.method as Method, base: preset.base.us, upper: preset.upper?.us ?? null }
      : parseSetting(token)
    if (!setting) continue
    const dd = preset ? preset.dd.us : settingText(setting)
    if (found.some((s) => s.dd === dd)) continue
    found.push({ token, dd, setting, preset })
  }
  return found
}

/** "Single sine, base 41 °F, upper 86 °F" in the reader's units */
export function settingWords(setting: Setting, units: Units): string {
  const method = METHODS.find((m) => m.value === setting.method)?.label ?? setting.method
  const temperature = (f: number) => units.format('degF', f, { digits: units.system === 'metric' ? 1 : 0 })
  const upper = setting.upper === null ? '' : `, upper ${temperature(setting.upper)}`
  return `${method}, base ${temperature(setting.base)}${upper}`
}

/** A series' name: the preset's ("Corn (field)"), or its setting in words */
export function seriesName(series: Series, units: Units): string {
  return series.preset ? series.preset.label : settingWords(series.setting, units)
}

/**
 * The day counting starts by default: a preset's biofix (an insect's `MM-DD`), else a crop's typical planting date at
 * the site (`/locate`'s `planting`), else the site's saved planting date, else May 1; in `year`.
 */
export function defaultStart({
  from,
  series,
  year,
  planting,
  saved,
  savedBiofix,
}: {
  from: CountFrom
  series: Series[]
  year: number
  planting?: { crop: string; typical: string }[] | null
  /** The site's planting date, from its preferences */
  saved?: string | null
  /** The site's biofix, from its preferences */
  savedBiofix?: string | null
}): { date: string; reason: string | null } {
  if (from === 'jan1') return { date: `${year}-01-01`, reason: null }
  if (from === 'biofix') {
    if (savedBiofix && savedBiofix.startsWith(`${year}-`))
      return { date: savedBiofix, reason: 'your biofix for this site' }
    const preset = series.find((s) => s.preset?.starts === 'biofix' && s.preset.biofix)?.preset
    if (preset && preset.biofix !== '01-01')
      return { date: `${year}-${preset.biofix}`, reason: `${preset.label}’s usual biofix` }
  }
  if (from === 'planting') {
    if (saved && saved.startsWith(`${year}-`)) return { date: saved, reason: 'your planting date for this site' }
    for (const s of series) {
      const crop = s.preset?.starts === 'planting' ? s.preset.crop_ids[0] : null
      const typical = crop ? planting?.find((p) => p.crop === crop)?.typical : null
      if (typical)
        return { date: `${year}-${typical}`, reason: `the typical ${s.preset!.label.toLowerCase()} planting date here` }
    }
  }
  return { date: `${year}-05-01`, reason: null }
}

/** The `/degree-days` query: every series in one request, from the start through the forecast (a past year through
 * December 31), or through `end` where one is chosen, with this year's projection when asked (and the end is still
 * ahead of today) */
export function ddQuery({
  lat,
  lng,
  series,
  start,
  year,
  thisYear,
  projection,
  end = null,
  today = null,
}: {
  lat: number
  lng: number
  series: Series[]
  /** The first day counted (January 1, or a planting date or biofix) */
  start: string
  year: number
  thisYear: number
  projection: boolean
  /** The last day counted, chosen (the calculator's): kept only within the season and on or after the start */
  end?: string | null
  /** Today, which a chosen end must be after for a projection */
  today?: string | null
}) {
  const last = ddEnd({ end, start, year })
  const ahead = last === null || today === null || last > today
  return {
    lat,
    lng,
    dd: series.map((s) => s.dd),
    start,
    end: last ?? (year < thisYear ? `${year}-12-31` : null),
    projection: year === thisYear && projection && ahead ? true : null,
    units: 'us',
  }
}

/** A chosen end date if it's in the season and not before the start, else null (count through the season) */
export function ddEnd({ end, start, year }: { end: string | null | undefined; start: string; year: number }) {
  return end && /^\d{4}-\d{2}-\d{2}$/.test(end) && end.startsWith(`${year}-`) && end >= start ? end : null
}

/** The map explorer showing the first setting's running total over the region, from the same start through the same
 * day, with the place marked (`/map?layer=degree_days&span=season&dd=…`); null without a setting */
export function ddMapUrl({
  lat,
  lng,
  series,
  start,
  end,
  year,
  thisYear,
}: {
  lat: number
  lng: number
  series: Series[]
  start: string
  /** The last day counted, if one is chosen */
  end: string | null
  year: number
  thisYear: number
}): string | null {
  const first = series[0]
  if (!first) return null
  const query = new URLSearchParams({ layer: 'degree_days', span: 'season', dd: first.dd })
  const date = end ?? (year < thisYear ? `${year}-12-31` : null)
  if (date) query.set('date', date)
  if (!start.endsWith('-01-01')) query.set('biofix', start)
  query.set('at', `${Number(lat.toFixed(4))},${Number(lng.toFixed(4))}`)
  return `${routes.map()}?${query.toString().replaceAll('%2C', ',')}`
}

export type DdRun = {
  table: Table
  series: Series[]
  /** Whether any row is projected */
  projected: boolean
  warnings: string[]
}

const daily = (s: Series) => `dd_${s.dd}`
const total = (s: Series) => `dd_${s.dd}_cum`

/** The answer as rows, each series' columns flagged estimated on the days whose temperatures were (the API's one
 * `temperature_estimated` column) */
export function ddRun(body: Pick<TableResponse, 'meta' | 'data'>, series: Series[]): DdRun {
  const table = tableRows(body)
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, unknown[]>
  const at = new Map(((data.date ?? []) as string[]).map((date, i) => [date, i]))
  const flagged = series.flatMap((s) => [daily(s), total(s)])
  const days = table.days.map((day): Day => {
    const estimated = data.temperature_estimated?.[at.get(day.date) ?? -1] === true
    return estimated ? { ...day, estimated: new Set([...day.estimated, ...flagged]) } : day
  })
  const shown = series.filter((s) => days.some((day) => daily(s) in day.values))
  return {
    table: { ...table, days },
    series: shown,
    projected: days.some((day) => day.kind === 'projection'),
    warnings: body.meta.warnings ?? [],
  }
}

const COLORS: ((p: Palette) => string)[] = [(p) => p.degreeDays, (p) => p.precipitation, (p) => p.temperature.max]
export const seriesColor = (k: number, palette: Palette) => COLORS[k % COLORS.length](palette)

const rounded = (value: number | null) => (value === null ? null : Number(value.toFixed(2)))

function shown(units: Units, value: number | null | undefined): number | null {
  return rounded(units.toDisplay(DD_UNIT, value ?? null))
}

/** The ECharts option: daily degree days as bars above, running totals as lines below, on one time axis */
export function ddOption({
  run,
  units,
  palette,
  today,
}: {
  run: DdRun
  units: Units
  palette: Palette
  today: string
}): EChartsCoreOption {
  const days = run.table.days
  const dates = days.map((day) => day.date)
  const base = baseOption(palette)
  const unit = units.label(DD_UNIT)
  const projected = days.map((day) => day.kind === 'projection')
  const firstProjected = projected.indexOf(true)
  const { shading, label: forecastLabel } = forecastBand({ dates, days, grids: 2, axisOffset: 2, palette })
  const marks = todayLine(dates, today, palette)
  const several = run.series.length > 1
  const name = (s: Series) => seriesName(s, units)

  const series: object[] = []
  run.series.forEach((s, k) => {
    const color = seriesColor(k, palette)
    const head = k === 0 ? { markLine: { silent: true, symbol: 'none', data: marks }, markArea: forecastLabel } : {}
    series.push({
      ...head,
      id: `daily-${s.dd}`,
      name: name(s),
      type: 'bar',
      xAxisIndex: 0,
      yAxisIndex: 0,
      barMaxWidth: several ? 4 : 8,
      itemStyle: { color },
      data: days.map((day, i) => {
        const value = shown(units, day.values[daily(s)])
        if (projected[i]) return value === null ? null : { value, itemStyle: { color, opacity: 0.4 } }
        return bar(value, day.estimated.has(daily(s)), color, palette)
      }),
    })
    const line = { type: 'line', xAxisIndex: 1, yAxisIndex: 1, symbol: 'circle', showSymbol: false, symbolSize: 4 }
    const totals = days.map((day) => shown(units, day.values[total(s)]))
    series.push({
      ...line,
      ...(k === 0
        ? { markLine: { silent: true, symbol: 'none', data: marks.map((m) => ({ ...m, label: { show: false } })) } }
        : {}),
      id: `total-${s.dd}`,
      name: name(s),
      connectNulls: false,
      itemStyle: { color },
      lineStyle: lineStyle(color),
      data: days.map((day, i) => (projected[i] ? null : point(totals[i], day.estimated.has(total(s)), palette))),
    })
    if (firstProjected > 0) {
      series.push({
        ...line,
        id: `projection-${s.dd}`,
        name: `${name(s)} (projection)`,
        itemStyle: { color },
        lineStyle: lineStyle(color, 'projection'),
        data: totals.map((value, i) => (i >= firstProjected - 1 ? value : null)),
      })
      const side = (suffix: string) =>
        days.map((day, i) => (projected[i] ? shown(units, day.values[`${total(s)}_${suffix}`]) : null))
      series.push(
        ...band({
          id: `projection-${s.dd}`,
          lower: side('p10'),
          upper: side('p90'),
          color: palette.projection,
          xAxisIndex: 1,
          yAxisIndex: 1,
        }),
      )
    }
  })

  const names = run.series.map(name)
  const timeZone = run.table.location?.timezone ?? undefined
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => rowLabel(date, timeZone, { short: true }) }
  const top = several ? 44 : 22
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: several
      ? {
          top: 0,
          left: 0,
          right: 0,
          type: 'scroll',
          data: names,
          textStyle: { color: palette.ink, fontSize: 11 },
          itemWidth: 14,
        }
      : undefined,
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        return list.length ? ddTooltip(run, units, list[0].dataIndex, palette) : ''
      },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: [
      { left: 52, right: 16, top, height: '28%' },
      { left: 52, right: 16, top: '50%', bottom: 24 },
    ],
    xAxis: [
      {
        type: 'category',
        data: dates,
        gridIndex: 0,
        axisLabel: { show: false },
        axisLine: base.axisLine,
        axisTick: { show: false },
      },
      { type: 'category', data: dates, gridIndex: 1, axisLabel, axisLine: base.axisLine },
      ...shading.xAxis,
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: 0,
        splitNumber: 2,
        name: `Daily (${unit})`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      {
        type: 'value',
        gridIndex: 1,
        min: 0,
        splitNumber: 3,
        name: `Running total (${unit})`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1, ...shading.xAxisIndexes] }],
    series: [...series, ...shading.series],
  }
}

function kindWords(day: Day): string {
  if (day.kind === 'projection') return ' (projection: the middle of past years)'
  if (day.kind === 'partial') return ' (today, partly forecast)'
  return isForecast(day) ? ' (forecast)' : ''
}

function ddTooltip(run: DdRun, units: Units, index: number, palette: Palette): string {
  const day = run.table.days[index]
  if (!day) return ''
  const timeZone = run.table.location?.timezone ?? undefined
  const rows = run.series.map((s, k) => {
    const marker = `<span style="display:inline-block;margin-right:4px;border-radius:9px;width:9px;height:9px;background:${seriesColor(k, palette)}"></span>`
    const estimated = day.estimated.has(daily(s)) ? ' (estimated)' : ''
    const range = rangeText(run, units, s, day)
    return `<tr><td style="padding-right:12px">${marker}${seriesName(s, units)}</td><td style="text-align:right">${units.format(DD_UNIT, day.values[daily(s)])} that day, <strong>${units.format(DD_UNIT, day.values[total(s)])}</strong> in all${range}${estimated}</td></tr>`
  })
  return `<strong>${rowLabel(day.date, timeZone)}${kindWords(day)}</strong><table>${rows.join('')}</table>`
}

/** ", 10–90% of past years 2,980 to 3,120 °F·d" on a projected day */
function rangeText(run: DdRun, units: Units, s: Series, day: Day): string {
  if (day.kind !== 'projection') return ''
  const low = day.values[`${total(s)}_p10`]
  const high = day.values[`${total(s)}_p90`]
  if (low == null || high == null) return ''
  return ` (likely ${units.format(DD_UNIT, low, { unit: false })} to ${units.format(DD_UNIT, high)})`
}

export type SeriesTotals = {
  series: Series
  /** The total on the last observed day (or today's, partly forecast), and that day */
  now: { date: string; value: number | null } | null
  /** At the forecast's end */
  forecast: { date: string; value: number | null } | null
  /** At the projection's end: P50, with P10 and P90 */
  projected: { date: string; p50: number | null; p10: number | null; p90: number | null } | null
  estimated: number
  missing: number
}

/** Each series' totals to date, at the forecast's end and at the projection's, with its estimated and missing days */
export function seriesTotals(run: DdRun, today: string): SeriesTotals[] {
  const days = run.table.days
  const past = days.filter((day) => day.kind !== 'projection' && !isForecast(day))
  const nowDay = days.find((day) => day.date === today && day.kind !== 'projection') ?? past.at(-1) ?? null
  const ahead = days.filter((day) => isForecast(day))
  const forecastDay = ahead.at(-1) ?? null
  const projectedDay = days.findLast((day) => day.kind === 'projection') ?? null
  return run.series.map((s) => ({
    series: s,
    now: nowDay ? { date: nowDay.date, value: nowDay.values[total(s)] ?? null } : null,
    forecast:
      forecastDay && forecastDay.date !== nowDay?.date
        ? { date: forecastDay.date, value: forecastDay.values[total(s)] ?? null }
        : null,
    projected: projectedDay
      ? {
          date: projectedDay.date,
          p50: projectedDay.values[total(s)] ?? null,
          p10: projectedDay.values[`${total(s)}_p10`] ?? null,
          p90: projectedDay.values[`${total(s)}_p90`] ?? null,
        }
      : null,
    estimated: days.filter((day) => day.kind !== 'projection' && day.estimated.has(daily(s))).length,
    missing: days.filter((day) => day.kind !== 'projection' && day.values[daily(s)] === null).length,
  }))
}

const plural = (count: number, word: string) => `${count} ${word}${count === 1 ? '' : 's'}`

/** "Counted from January 1, 2026" or "from the planting date, May 13, 2026" */
export function startWords(from: CountFrom, start: string): string {
  const when = formatDate(start, { year: true })
  if (from === 'planting') return `Counted from planting on ${when}`
  if (from === 'biofix') return `Counted from the biofix, ${when}`
  return `Counted from ${when}`
}

/** The chart in words: each series' total to date, at the forecast's end and projected, and its estimated days
 * (D45: "includes N estimated days") */
export function ddWords({
  run,
  units,
  today,
  from,
  start,
}: {
  run: DdRun
  units: Units
  today: string
  from: CountFrom
  start: string
}): string {
  if (!run.table.days.length || !run.series.length) return 'No degree days for these days yet.'
  const sentences = [`${startWords(from, start)}.`]
  for (const t of seriesTotals(run, today)) {
    const parts: string[] = []
    if (t.now) parts.push(`${units.format(DD_UNIT, t.now.value)} through ${formatDate(t.now.date)}`)
    if (t.forecast)
      parts.push(`${units.format(DD_UNIT, t.forecast.value)} by ${formatDate(t.forecast.date)} (forecast)`)
    if (t.projected && t.projected.p50 !== null)
      parts.push(
        `about ${units.format(DD_UNIT, t.projected.p50)} by ${formatDate(t.projected.date)} on past years’ weather (likely ${units.format(DD_UNIT, t.projected.p10, { unit: false })} to ${units.format(DD_UNIT, t.projected.p90)})`,
      )
    let sentence = `${seriesName(t.series, units)}: ${parts.join('; ')}.`
    if (t.estimated) sentence += ` Includes ${plural(t.estimated, 'estimated day')}.`
    if (t.missing) sentence += ` ${plural(t.missing, 'day')} missing, which add nothing.`
    sentences.push(sentence)
  }
  return sentences.join(' ')
}

/** "Summary and data"'s table, newest first: each series' daily value and running total */
export function ddTable(run: DdRun, units: Units) {
  const unit = units.label(DD_UNIT)
  const columns = run.series.flatMap((s) => {
    const name = seriesName(s, units)
    return [`${name}, daily (${unit})`, `${name}, total (${unit})`]
  })
  return {
    columns,
    rows: run.table.days.toReversed().map((day) => ({
      date: day.date,
      forecast: isForecast(day) || day.kind === 'projection',
      values: run.series.flatMap((s) =>
        [daily(s), total(s)].map((column) => {
          const value = units.toDisplay(DD_UNIT, day.values[column] ?? null)
          if (value === null) return null
          return `${value.toFixed(0)}${day.estimated.has(column) ? ' (estimated)' : ''}${day.kind === 'projection' ? ' (projected)' : ''}`
        }),
      ),
    })),
  }
}

/** The values for a CSV file, oldest first: Date, Kind, then each series' daily value and total in the reader's
 * units (a projection's P10 and P90 too), and whether the day's temperatures were estimated; missing is blank */
export function ddCsvRows(run: DdRun, units: Units): CsvValue[][] {
  const unit = units.label(DD_UNIT)
  const projected = run.projected
  const header = ['Date', 'Kind']
  for (const s of run.series) {
    const name = seriesName(s, units)
    header.push(`${name}, daily (${unit})`, `${name}, total (${unit})`)
    if (projected) header.push(`${name}, total P10 (${unit})`, `${name}, total P90 (${unit})`)
  }
  header.push('Temperatures estimated')
  const value = (day: Day, column: string) => {
    const shownValue = units.toDisplay(DD_UNIT, day.values[column] ?? null)
    return shownValue === null ? null : Number(shownValue.toFixed(1))
  }
  return [
    header,
    ...run.table.days.map((day) => {
      const row: CsvValue[] = [day.date, day.kind]
      for (const s of run.series) {
        row.push(value(day, daily(s)), value(day, total(s)))
        if (projected) row.push(value(day, `${total(s)}_p10`), value(day, `${total(s)}_p90`))
      }
      row.push(day.kind === 'projection' ? null : day.estimated.size ? 'yes' : 'no')
      return row
    }),
  ]
}
