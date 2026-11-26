// The crop GDD outlook (`/tools/crop-gdd`, track 5 P1): growing degree days since planting at a place, with when the
// crop reaches its stages (corn's from the corn stage model, another crop's maturity from the degree days the reader
// types), against the normal and up to three past years, and the chance of a fall freeze before maturity. Pure
// functions over the API's answers, all in °F and °F·d (the page asks with `units=us`, converting at display).
//
//   const outlook = outlookFromRun(runBody) ?? outlookFromDegreeDays({ body, setting, planting, targets })
//   const normal = normalCurve({ table: compareTable(body), setting, dates: outlook.dates })
//   const years = yearCurve({ body, setting, dates: outlook.dates })
//   outlookAnswer({ ... })                     // the answer in words
//   stageRows({ outlook, normal, years })      // the table
//   cropGddOption({ ... })                     // the chart: GDD since planting over the fall freeze chance

import type { TableResponse } from '@/types/api'

import { normalBand, normalName, type CompareTable, type FreezeChances } from '../charts/climateCharts'
import type { EChartsCoreOption } from '../charts/echarts'
import { band, rounded, rowLabel, thresholdLine, todayLine } from '../charts/kinds'
import { baseOption, type Palette } from '../charts/palette'
import { forecastShading } from '../charts/shading'
import { formatDate } from '../dates'
import { columnsOf, type Kind } from '../tableRows'
import type { Units } from '../units'
import type { PeriodYears } from '../climate/periods'
import { freezeNoun } from './freeze'
import { plural } from '../words'

type Body = Pick<TableResponse, 'meta' | 'data'>
const record = (value: unknown) => (value && typeof value === 'object' ? (value as Record<string, unknown>) : {})
const numberOr = (value: unknown) => (typeof value === 'number' && Number.isFinite(value) ? value : null)
const textOr = (value: unknown) => (typeof value === 'string' ? value : null)

// --- The crops ----------------------------------------------------------------------------------------------------

/** A crop the tool offers: a degree-day preset counted from planting (`/degree-days/presets`) */
export type CropChoice = {
  id: string
  label: string
  /** The degree-day setting in °F, as `dd=` takes it with `units=us` (`modified_50_86`) */
  setting: string
  /** The crop's own stage model (`corn-stages`), or null */
  model: string | null
  /** The preset's killing freeze, °F, or null without one */
  freezeF: number | null
  freezeNote: string | null
  notes: string | null
}

type PresetLike = {
  id: string
  group: string
  label: string
  starts?: string | null
  model?: string | null
  notes?: string | null
  dd: { us: string }
  freeze?: { temperature: { us: number }; note?: string | null } | null
}

/** The crops counted from planting, corn first (alfalfa, counted from January 1 or a cutting, has its own tool) */
export function cropChoices(presets: readonly PresetLike[]): CropChoice[] {
  const crops = presets
    .filter((p) => p.group === 'crop' && p.starts === 'planting')
    .map((p) => ({
      id: p.id,
      label: p.label,
      setting: p.dd.us,
      model: p.model ?? null,
      freezeF: p.freeze?.temperature.us ?? null,
      freezeNote: p.freeze?.note ?? null,
      notes: p.notes ?? null,
    }))
  return [...crops.filter((c) => c.id === 'corn'), ...crops.filter((c) => c.id !== 'corn')]
}

/** The freeze a crop without a killing freeze of its own is shown against: a hard freeze */
export const DEFAULT_FREEZE_F = 28

/** The range a reader's own freeze temperature may take, °F (as the freeze tool's) */
export const FREEZE_RANGE_F = { min: -20, max: 40 } as const

/** The range of a typed maturity, °F·d */
export const TARGET_RANGE_F = { min: 50, max: 6000 } as const

/** The planting date when neither the reader nor `/locate` gives one */
export const FALLBACK_PLANTING = '05-15'

/** Corn's stages the table lists, and those the chart marks (a line each; the rest would crowd it) */
export const TABLE_STAGES = ['VE', 'V6', 'V10', 'VT', 'R1', 'R2', 'R3', 'R4', 'R5', 'R5.5', 'R6'] as const
export const CHART_STAGES = ['VE', 'V6', 'R1', 'R5', 'R6'] as const

/** Corn's maturity stage */
export const MATURITY = 'R6'

/** The comparison years a reader may add */
export const MAX_YEARS = 3

/** The comparison years as the view keeps them: `2012,2020` */
export const yearsCodec = {
  parse(text: string): number[] | undefined {
    const years = text
      .split(',')
      .map((part) => Number(part.trim()))
      .filter((y) => Number.isInteger(y) && y >= 1940 && y <= 2100)
    const unique = [...new Set(years)].slice(0, MAX_YEARS)
    return unique.length ? unique : undefined
  },
  format: (years: number[]) => years.join(','),
}

// --- The outlook --------------------------------------------------------------------------------------------------

/** A degree-day total the crop reaches: a stage (`R1`, Silking) or the reader's maturity */
export type Target = { code: string; name: string; gdd: number; estimated: boolean }

/** When a target is reached: `p50` (with `p10`–`p90` from past years' weather after the forecast), or the day it was
 * or is forecast to be (all three the same); `reached` of `of` series reach it by the end */
export type TargetDate = Target & {
  p10: string | null
  p50: string | null
  p90: string | null
  reached: number
  of: number
  /** How `p50` is known: observed, forecast, projected from past years, or not reached at all */
  status: 'reached' | 'forecast' | 'projected' | 'none'
}

export type Outlook = {
  /** From planting through December 31 */
  dates: string[]
  /** Each day's kind; null where there's no value (past the forecast without a projection) */
  kinds: (Kind | null)[]
  /** GDD since planting (°F·d): observed, forecast, then the projection's middle (P50) */
  total: (number | null)[]
  /** The projection's 10th and 90th percentiles; null before it */
  low: (number | null)[]
  high: (number | null)[]
  targets: TargetDate[]
  /** The past years the projection takes its weather from */
  projectionYears: number[]
  warnings: string[]
  /** Which answer it came from: the crop's own model, or `/degree-days` */
  source: 'model' | 'degree-days'
}

const KINDS: readonly string[] = ['observed', 'partial', 'forecast', 'projection']
const kindOf = (value: unknown): Kind | null => (KINDS.includes(value as string) ? (value as Kind) : null)

function statusOf(p50: string | null, p10: string | null, p90: string | null, at: Map<string, Kind | null>) {
  if (!p50) return 'none' as const
  const kind = at.get(p50) ?? null
  if (kind === 'observed') return 'reached' as const
  if ((kind === 'forecast' || kind === 'partial') && p10 === p50 && p90 === p50) return 'forecast' as const
  return 'projected' as const
}

/** The thresholds a crop model's run gives its stages (`meta.summary.stages`), those `codes` names, in order */
export function stageTargets(body: Body, codes: readonly string[] = TABLE_STAGES): Target[] {
  const stages = (record(body.meta.summary).stages ?? []) as Record<string, unknown>[]
  return stages
    .filter((s) => codes.includes(String(s.code)) && numberOr(s.threshold) !== null)
    .map((s) => ({
      code: String(s.code),
      name: String(s.name ?? s.code),
      gdd: s.threshold as number,
      estimated: s.estimated === true,
    }))
}

/** The corn stage model's run (`/models/corn-stages/run?…&projection=true&end=<Dec 31>`) as an outlook; null when
 * it has nothing to show (a planting date past the forecast's end, which a model run can't project from) */
export function outlookFromRun(body: Body, codes: readonly string[] = TABLE_STAGES): Outlook | null {
  const data = columnsOf(body)
  const dates = (data.date ?? []) as string[]
  const kinds = ((data.kind ?? []) as unknown[]).map(kindOf)
  if (!kinds.some((k) => k !== null)) return null
  const column = (name: string) => ((data[name] ?? []) as unknown[]).map(numberOr)
  const total = column('gdd_total').map((v, i) => (kinds[i] ? v : null))
  const summary = record(body.meta.summary)
  const projection = record(summary.projection)
  const at = new Map(dates.map((d, i) => [d, kinds[i]]))
  // With a projection, each stage's percentiles; without one (nothing left to project), the day it was reached
  const projected = (projection.milestones ?? null) as Record<string, unknown>[] | null
  const plain = (summary.milestones ?? []) as Record<string, unknown>[]
  const targets = stageTargets(body, codes).map((target): TargetDate => {
    const found = projected?.find((m) => m.what === 'stage' && m.name === target.code)
    if (found) {
      const [p10, p50, p90] = [textOr(found.p10), textOr(found.p50), textOr(found.p90)]
      return {
        ...target,
        p10,
        p50,
        p90,
        reached: numberOr(found.reached) ?? 0,
        of: numberOr(found.of) ?? 0,
        status: statusOf(p50, p10, p90, at),
      }
    }
    const once = plain.find((m) => m.what === 'stage' && m.name === target.code)
    const date = textOr(once?.date)
    return {
      ...target,
      p10: date,
      p50: date,
      p90: date,
      reached: date ? 1 : 0,
      of: 1,
      status: statusOf(date, date, date, at),
    }
  })
  return {
    dates,
    kinds,
    total,
    low: column('gdd_total_p10'),
    high: column('gdd_total_p90'),
    targets,
    projectionYears: ((projection.years ?? []) as number[]).filter((y) => typeof y === 'number'),
    warnings: body.meta.warnings ?? [],
    source: 'model',
  }
}

/** `/degree-days?dd=<setting>&biofix=<planting>&projection=true&end=<Dec 31>&targets=…` as an outlook from planting,
 * the targets named as given (their `gdd` as sent in `targets=`) */
export function outlookFromDegreeDays({
  body,
  setting,
  planting,
  targets,
}: {
  body: Body
  setting: string
  planting: string
  targets: Target[]
}): Outlook {
  const data = columnsOf(body)
  const all = (data.date ?? []) as string[]
  const from = all.findIndex((d) => d >= planting)
  const keep = <T>(values: T[]) => (from < 0 ? [] : values.slice(from))
  const dates = keep(all)
  const kinds = keep(((data.kind ?? []) as unknown[]).map(kindOf))
  const column = (name: string) => keep(((data[name] ?? []) as unknown[]).map(numberOr))
  const cum = `dd_${setting}_cum`
  const total = column(cum).map((v, i) => (kinds[i] ? v : null))
  const summary = record(body.meta.summary)
  const projection = record(Array.isArray(summary.projection) ? summary.projection[0] : summary.projection)
  const found = ((summary.targets ?? []) as Record<string, unknown>[]).filter(
    (t) => t.setting === setting && (t.point ?? 0) === 0,
  )
  const at = new Map(dates.map((d, i) => [d, kinds[i]]))
  return {
    dates,
    kinds,
    total,
    low: column(`${cum}_p10`),
    high: column(`${cum}_p90`),
    targets: targets.map((target): TargetDate => {
      const hit = found.find((t) => Math.abs((numberOr(t.target) ?? NaN) - target.gdd) < 0.01)
      const [p10, p50, p90] = [textOr(hit?.p10), textOr(hit?.p50), textOr(hit?.p90)]
      return {
        ...target,
        p10,
        p50,
        p90,
        reached: numberOr(hit?.reached) ?? 0,
        of: numberOr(hit?.of) ?? 0,
        status: statusOf(p50, p10, p90, at),
      }
    }),
    projectionYears: ((projection.years ?? []) as number[]).filter((y) => typeof y === 'number'),
    warnings: body.meta.warnings ?? [],
    source: 'degree-days',
  }
}

/** The latest total that isn't projected (observed or forecast), with its day */
export function latestTotal(outlook: Outlook): { date: string; gdd: number; kind: Kind } | null {
  for (let i = outlook.dates.length - 1; i >= 0; i--) {
    const kind = outlook.kinds[i]
    const value = outlook.total[i]
    if (kind && kind !== 'projection' && value !== null) return { date: outlook.dates[i], gdd: value, kind }
  }
  return null
}

// --- The normal and the comparison years --------------------------------------------------------------------------

export type Curve = { mean: (number | null)[]; low: (number | null)[]; high: (number | null)[] }

/** `/climate/compare?dd=<setting>&start=<planting>`'s normal from planting (mean and its 10th–90th percentiles),
 * aligned to the outlook's dates */
export function normalCurve({
  table,
  setting,
  dates,
}: {
  table: CompareTable
  setting: string
  dates: string[]
}): Curve {
  const at = new Map(table.dates.map((d, i) => [d, i]))
  const pick = (suffix: string) => {
    const values = table.values[`dd_${setting}_cum_normal${suffix}`] ?? []
    return dates.map((d) => {
      const i = at.get(d)
      return i === undefined ? null : (values[i] ?? null)
    })
  }
  return { mean: pick(''), low: pick('_p10'), high: pick('_p90') }
}

/** A past year's GDD since its own planting date (`/degree-days?dd=<setting>&biofix=<year>-<MM-DD>&end=<year>-12-31`),
 * by month and day on the outlook's dates */
export type YearCurve = { year: number; values: (number | null)[]; dates: string[]; openMeteo: boolean }

export function yearCurve({ body, setting, dates }: { body: Body; setting: string; dates: string[] }): YearCurve {
  const data = columnsOf(body)
  const own = (data.date ?? []) as string[]
  const cum = ((data[`dd_${setting}_cum`] ?? []) as unknown[]).map(numberOr)
  const byDay = new Map(own.map((d, i) => [d.slice(5), cum[i]]))
  const year = Number((own[0] ?? '').slice(0, 4))
  return {
    year,
    values: dates.map((d) => byDay.get(d.slice(5)) ?? null),
    dates: dates.map((d) => `${year}-${d.slice(5)}`),
    openMeteo: !!body.meta.sources?.includes('openmeteo'),
  }
}

/** The first of `dates` whose value reaches `gdd`, or null */
export function dateReaching(dates: string[], values: (number | null)[], gdd: number): string | null {
  const i = values.findIndex((v) => v !== null && v >= gdd)
  return i < 0 ? null : dates[i]
}

// --- The freeze chance --------------------------------------------------------------------------------------------

/** The chance (percent) that the first fall freeze at `fahrenheit` has come by `date` (its month and day), from
 * `/climate/frost/chances`; 0 before July (a freeze then is spring's), null without the threshold */
export function fallChance(chances: FreezeChances | null, fahrenheit: number, date: string): number | null {
  if (!chances) return null
  const values = chances.chance[String(fahrenheit)]
  if (!values) return null
  const i = chances.dates.findIndex((d) => d.slice(5) === date.slice(5))
  if (i < 0) return null
  if (chances.season[i] !== 'fall') return 0
  return values[i] ?? null
}

/** Each of `dates`' fall freeze chance, null in spring (January–June), for the chart's lower grid */
export function fallChances(chances: FreezeChances | null, fahrenheit: number, dates: string[]): (number | null)[] {
  if (!chances) return dates.map(() => null)
  const values = chances.chance[String(fahrenheit)] ?? []
  const byDay = new Map(chances.dates.map((d, i) => [d.slice(5), i]))
  return dates.map((d) => {
    const i = byDay.get(d.slice(5))
    if (i === undefined || chances.season[i] !== 'fall') return null
    return values[i] ?? null
  })
}

// --- The answer in words ------------------------------------------------------------------------------------------

/** What's grown: "A 2700 GDD hybrid planted May 8" or "Soybean planted May 17" */
export function subjectWords({ crop, hybrid, planting }: { crop: string; hybrid: string | null; planting: string }) {
  const what = hybrid ? `A ${hybrid} GDD hybrid` : crop
  return `${what} planted ${formatDate(planting)}`
}

/**
 * The answer: when the crop reached or should reach `maturity` (corn's black layer, or the reader's own total),
 * with the range from past years' weather and the chance of a fall freeze before then; after the season, the date
 * reached. `what` names the target inside a sentence ("black layer", "2,400 °F·d").
 */
export function outlookAnswer({
  subject,
  what,
  maturity,
  latest,
  normalDate,
  freezeF,
  chance,
  units,
}: {
  subject: string
  what: string
  maturity: TargetDate
  latest: { date: string; gdd: number; kind: Kind } | null
  normalDate: string | null
  freezeF: number
  /** The chance (percent) of the fall freeze by maturity's middle date, or null while it's unknown */
  chance: number | null
  units: Units
}): { headline: string; details: string[] } {
  const details: string[] = []
  const freeze = freezeNoun(freezeF, units)
  const chanceText = (by: 'before then' | 'by then') =>
    chance === null ? '' : `, with a ${Math.round(chance)}% chance of a ${freeze} ${by}`
  const normalLine = normalDate ? `In a normal year it would reach ${what} on ${formatDate(normalDate)}.` : null
  const { p10, p50, p90, reached, of } = maturity
  let headline: string
  switch (maturity.status) {
    case 'reached':
      headline = `${subject} reached ${what} on ${formatDate(p50)}.`
      if (normalDate) details.push(`In a normal year it would have reached it on ${formatDate(normalDate)}.`)
      break
    case 'forecast':
      headline = `${subject} is forecast to reach ${what} on ${formatDate(p50)}${chanceText('by then')}.`
      if (normalLine) details.push(normalLine)
      break
    case 'projected': {
      const range = p10 && p90 && p10 !== p90 ? ` (likely ${formatDate(p10)} to ${formatDate(p90)})` : ''
      headline = `${subject} is projected to reach ${what} about ${formatDate(p50)}${range}${chanceText('before then')}.`
      if (reached < of) {
        details.push(
          `With the weather of ${plural(of, 'past year')} after the forecast, it got there by December 31 in ${reached} of them; the dates are from those years.`,
        )
      }
      if (normalLine) details.push(normalLine)
      break
    }
    case 'none': {
      const total = latest ? units.format('degF_day', latest.gdd, { digits: 0 }) : null
      if (of > 1) {
        const share = reached > 0 ? `in only ${reached} of them` : 'in none of them'
        headline = `${subject} is unlikely to reach ${what} this year: with the weather of ${plural(of, 'past year')} after the forecast, it got there by December 31 ${share}.`
        if (total && latest) details.push(`So far: ${total} through ${formatDate(latest.date)}.`)
      } else if (total && latest) {
        headline = `${subject} had ${total} by ${formatDate(latest.date)}, short of ${what}.`
      } else {
        headline = `${subject} has not reached ${what}.`
      }
      if (normalLine) details.push(normalLine)
      break
    }
  }
  if (latest && maturity.status !== 'reached' && maturity.status !== 'none') {
    const ahead = latest.kind === 'observed' ? 'so far' : `through the forecast (${formatDate(latest.date)})`
    details.unshift(`${units.format('degF_day', latest.gdd, { digits: 0 })} since planting ${ahead}.`)
  }
  return { headline, details }
}

// --- The table ----------------------------------------------------------------------------------------------------

export type StageRow = {
  code: string
  name: string
  gdd: number
  estimated: boolean
  /** This year's date, or the projection's middle date with its range, in words */
  thisYear: string
  status: TargetDate['status']
  normal: string | null
  /** Each comparison year's date, in order */
  years: (string | null)[]
}

/** This year's date for a target in a table cell: "Sep 27", "Oct 2 (forecast)", "Oct 3 (Sep 25 – Oct 12)",
 * "Not reached" */
export function dateText(target: TargetDate): string {
  const { p10, p50, p90, status, reached, of } = target
  if (status === 'reached') return formatDate(p50)
  if (status === 'forecast') return `${formatDate(p50)} (forecast)`
  if (status === 'projected') {
    const range = p10 && p90 && p10 !== p90 ? ` (${formatDate(p10)} – ${formatDate(p90)})` : ''
    const share = reached < of ? `, ${reached} of ${of} years` : ''
    return `About ${formatDate(p50)}${range}${share}`
  }
  if (of > 1 && reached > 0) return `${reached} of ${of} years`
  return 'Not reached'
}

export function stageRows({
  outlook,
  normal,
  years,
}: {
  outlook: Outlook
  normal: Curve | null
  years: YearCurve[]
}): StageRow[] {
  return outlook.targets.map((target) => ({
    code: target.code,
    name: target.name,
    gdd: target.gdd,
    estimated: target.estimated,
    thisYear: dateText(target),
    status: target.status,
    normal: normal ? dateReaching(outlook.dates, normal.mean, target.gdd) : null,
    years: years.map((y) => dateReaching(y.dates, y.values, target.gdd)),
  }))
}

// --- The chart ----------------------------------------------------------------------------------------------------

/** The comparison years' line colors (thin, solid, told apart by their legend and tooltip, never color alone) */
const yearColors = (palette: Palette) => [palette.temperature.max, palette.precipitation, palette.et]

/**
 * Two grids on one time axis, from planting through December 31: above, GDD since planting (observed solid, the
 * forecast shaded, then the projection's middle dashed over its 10th–90th percentile band), the normal dashed over
 * its usual range, each comparison year thin, and the stages as labelled lines; below, the chance the first fall
 * freeze at `freezeF` has come by each date. A dashed Today line runs through both.
 */
export function cropGddOption({
  outlook,
  normal,
  normalYears,
  years,
  stages,
  chances,
  freezeF,
  units,
  palette,
  today,
}: {
  outlook: Outlook
  normal: Curve | null
  normalYears: PeriodYears | null
  years: YearCurve[]
  /** The stage lines to draw (their gdd in °F·d) */
  stages: Target[]
  chances: (number | null)[]
  freezeF: number
  units: Units
  palette: Palette
  today: string
}): EChartsCoreOption {
  const base = baseOption(palette)
  const { dates, kinds } = outlook
  const shown = (values: (number | null)[]) => values.map((v) => rounded(units.toDisplay('degF_day', v) ?? null))
  const unit = units.label('degF_day')
  const color = palette.degreeDays

  const projectionFrom = kinds.findIndex((k) => k === 'projection')
  const forecastFrom = kinds.findIndex((k) => k === 'forecast' || k === 'partial')
  const shading = forecastShading({ dates, from: forecastFrom, grids: 2, axisOffset: 2, palette })
  // The shading covers the forecast's days only: a projection is told by its dashes and band
  const shadingSeries = shading.series.map((s) => ({
    ...s,
    data: (s as { data: (number | null)[] }).data.map((v, i) =>
      kinds[i] === 'forecast' || kinds[i] === 'partial' ? v : null,
    ),
  }))

  const total = shown(outlook.total)
  // Observed and forecast solid; the projection dashed, joined to the last day before it
  const solid = total.map((v, i) => (projectionFrom < 0 || i < projectionFrom ? v : null))
  const dashed = total.map((v, i) => (projectionFrom >= 0 && i >= projectionFrom - 1 ? v : null))
  const thisYear = dates[0]?.slice(0, 4) ?? ''
  const normalLabel = normalName(normalYears)
  const projectionName = `${thisYear}, projected`
  const rangeName = 'Projection, 10th–90th percentile'

  const stageMarks = stages.map((s) => thresholdLine(units.toDisplay('degF_day', s.gdd) ?? s.gdd, s.code, palette))
  const series: object[] = []
  if (normal) {
    series.push(
      ...normalBand({
        id: 'normal',
        dates,
        mean: shown(normal.mean),
        low: shown(normal.low),
        high: shown(normal.high),
        color: palette.normal,
        name: normalLabel,
      }),
    )
  }
  if (projectionFrom >= 0) {
    const [lower, upper] = band({
      id: 'projection',
      lower: shown(outlook.low).map((v, i) => (i >= projectionFrom ? v : null)),
      upper: shown(outlook.high).map((v, i) => (i >= projectionFrom ? v : null)),
      color: palette.projection,
    }) as [object, object]
    series.push(lower, { ...upper, name: rangeName })
  }
  const yearPalette = yearColors(palette)
  years.forEach((y, k) => {
    series.push({
      id: `year-${y.year}`,
      name: String(y.year),
      type: 'line',
      data: shown(y.values),
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 1.25, color: yearPalette[k % yearPalette.length], opacity: 0.9 },
      itemStyle: { color: yearPalette[k % yearPalette.length] },
    })
  })
  series.push({
    id: 'this-year',
    name: thisYear,
    type: 'line',
    data: solid,
    symbol: 'none',
    connectNulls: false,
    lineStyle: { width: 2.5, color },
    itemStyle: { color },
    markLine: { silent: true, symbol: 'none', data: [...todayLine(dates, today, palette), ...stageMarks] },
  })
  if (projectionFrom >= 0) {
    series.push({
      id: 'projection',
      name: projectionName,
      type: 'line',
      data: dashed,
      symbol: 'none',
      connectNulls: false,
      lineStyle: { width: 2, color, type: 'dashed' },
      itemStyle: { color },
    })
  }
  const freezeName = `Chance of a ${freezeNoun(freezeF, units)} by this date`
  series.push({
    id: 'freeze',
    name: freezeName,
    type: 'line',
    xAxisIndex: 1,
    yAxisIndex: 1,
    data: chances.map((v) => (v === null ? null : Math.round(v))),
    symbol: 'none',
    connectNulls: false,
    lineStyle: { width: 2, color: palette.temperature.min },
    itemStyle: { color: palette.temperature.min },
    areaStyle: { color: palette.temperature.min, opacity: 0.12 },
    markLine: { silent: true, symbol: 'none', data: todayLine(dates, today, palette) },
  })

  const legend = series
    .map((s) => (s as { name?: string }).name)
    .filter((name): name is string => !!name && !name.endsWith(' lower') && name !== 'normal band')
  const axisLabel = { ...base.axisLabel, formatter: (date: string) => rowLabel(date, undefined, { short: true }) }
  const tooltip = (index: number) =>
    cropGddTooltip({
      index,
      outlook,
      normal,
      normalLabel,
      years,
      chances,
      freezeF,
      units,
      palette,
      yearPalette,
    })

  return {
    animation: base.animation,
    textStyle: base.textStyle,
    legend: {
      type: 'scroll',
      top: 0,
      left: 0,
      right: 0,
      data: legend,
      textStyle: { color: palette.ink, fontSize: 11 },
      itemWidth: 14,
    },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        const index = list[0]?.dataIndex
        return index === undefined ? '' : tooltip(index)
      },
    },
    axisPointer: { link: [{ xAxisIndex: [0, 1] }] },
    grid: [
      { left: 56, right: 16, top: 52, height: '58%' },
      { left: 56, right: 16, bottom: 24, height: '18%' },
    ],
    xAxis: [
      { type: 'category', data: dates, gridIndex: 0, axisLabel: { show: false }, axisLine: base.axisLine },
      { type: 'category', data: dates, gridIndex: 1, axisLabel, axisLine: base.axisLine },
      ...shading.xAxis,
    ],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: 0,
        name: `GDD since planting (${unit})`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 8,
        splitNumber: 4,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      {
        type: 'value',
        gridIndex: 1,
        min: 0,
        max: 100,
        interval: 50,
        name: `Fall ${freezeNoun(freezeF, units)} by date (%)`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        nameGap: 6,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1, ...shading.xAxisIndexes] }],
    series: [...series, ...shadingSeries],
  }
}

function cropGddTooltip({
  index,
  outlook,
  normal,
  normalLabel,
  years,
  chances,
  freezeF,
  units,
  palette,
  yearPalette,
}: {
  index: number
  outlook: Outlook
  normal: Curve | null
  normalLabel: string
  years: YearCurve[]
  chances: (number | null)[]
  freezeF: number
  units: Units
  palette: Palette
  yearPalette: string[]
}): string {
  const gdd = (value: number | null | undefined) =>
    value === null || value === undefined ? 'None' : units.format('degF_day', value, { digits: 0 })
  const swatch = (color: string) =>
    `<span style="display:inline-block;margin-right:4px;border-radius:9px;width:9px;height:9px;background:${color}"></span>`
  const row = (label: string, value: string) =>
    `<tr><td style="padding-right:12px">${label}</td><td style="text-align:right">${value}</td></tr>`
  const date = outlook.dates[index]
  const kind = outlook.kinds[index]
  const rows: string[] = []
  const value = outlook.total[index]
  if (value !== null && value !== undefined) {
    const low = outlook.low[index]
    const high = outlook.high[index]
    const range =
      kind === 'projection' && low !== null && high !== null && low !== high ? ` (${gdd(low)} to ${gdd(high)})` : ''
    const note = kind === 'projection' ? ', projected' : kind === 'forecast' || kind === 'partial' ? ', forecast' : ''
    rows.push(row(`${swatch(palette.degreeDays)}${date.slice(0, 4)}${note}`, `<strong>${gdd(value)}</strong>${range}`))
  }
  if (normal && normal.mean[index] !== null) {
    const low = normal.low[index]
    const high = normal.high[index]
    const range = low !== null && high !== null ? `, usually ${gdd(low)} to ${gdd(high)}` : ''
    rows.push(row(`${swatch(palette.normal)}${normalLabel}`, `${gdd(normal.mean[index])}${range}`))
  }
  years.forEach((y, k) => {
    rows.push(row(`${swatch(yearPalette[k % yearPalette.length])}${y.year}`, gdd(y.values[index])))
  })
  const chance = chances[index]
  if (chance !== null && chance !== undefined) {
    rows.push(
      row(
        `${swatch(palette.temperature.min)}Chance of a ${freezeNoun(freezeF, units)} by now`,
        `${Math.round(chance)}%`,
      ),
    )
  }
  return `<strong>${formatDate(date, { weekday: true })}</strong><table>${rows.join('')}</table>`
}

/** The chart in words: its text alternative and summary */
export function cropGddSummary({
  outlook,
  maturity,
  normalDate,
  freezeF,
  units,
}: {
  outlook: Outlook
  maturity: TargetDate | null
  normalDate: string | null
  freezeF: number
  units: Units
}): string {
  const last = latestTotal(outlook)
  const parts: string[] = []
  if (last)
    parts.push(`${units.format('degF_day', last.gdd, { digits: 0 })} since planting through ${formatDate(last.date)}.`)
  if (maturity) parts.push(`${maturity.name}: ${dateText(maturity)}.`)
  if (normalDate) parts.push(`A normal year reaches it on ${formatDate(normalDate)}.`)
  parts.push(
    `The lower chart shows the chance that the first fall ${freezeNoun(freezeF, units)} has come by each date.`,
  )
  return parts.join(' ')
}

/** "Summary and data"'s table: each day's GDD since planting, the projection's range, the normal and the freeze
 * chance, newest first */
export function cropGddRows({
  outlook,
  normal,
  years,
  chances,
  units,
}: {
  outlook: Outlook
  normal: Curve | null
  years: YearCurve[]
  chances: (number | null)[]
  units: Units
}) {
  const unit = units.label('degF_day')
  const gdd = (value: number | null | undefined) =>
    value === null || value === undefined ? null : units.format('degF_day', value, { digits: 0, unit: false })
  return {
    columns: [
      `GDD since planting (${unit})`,
      `Projection, 10th percentile (${unit})`,
      `Projection, 90th percentile (${unit})`,
      `Normal (${unit})`,
      ...years.map((y) => `${y.year} (${unit})`),
      'Fall freeze by date (%)',
    ],
    rows: outlook.dates
      .map((date, i) => ({
        date,
        forecast: outlook.kinds[i] !== 'observed',
        values: [
          gdd(outlook.total[i]),
          outlook.kinds[i] === 'projection' ? gdd(outlook.low[i]) : null,
          outlook.kinds[i] === 'projection' ? gdd(outlook.high[i]) : null,
          gdd(normal?.mean[i]),
          ...years.map((y) => gdd(y.values[i])),
          chances[i] === null || chances[i] === undefined ? null : String(Math.round(chances[i]!)),
        ],
      }))
      .filter((r) => r.values.some((v) => v !== null))
      .toReversed(),
  }
}

// --- Settings -----------------------------------------------------------------------------------------------------

/** The planting date: the reader's, else `/locate`'s typical date for the crop, else the model's default, else May 15 */
export function plantingDate({
  chosen,
  typical,
  fallback,
  year,
}: {
  chosen: string | null
  /** MM-DD */
  typical: string | null
  /** MM-DD */
  fallback: string | null
  year: number
}): { date: string; from: 'chosen' | 'typical' | 'fallback' } {
  if (chosen && Number(chosen.slice(0, 4)) === year) return { date: chosen, from: 'chosen' }
  if (typical) return { date: `${year}-${typical}`, from: 'typical' }
  return { date: `${year}-${fallback ?? FALLBACK_PLANTING}`, from: 'fallback' }
}

/** The comparison years a reader may choose: the 30 before this one, newest first */
export const comparisonYears = (thisYear: number): number[] => Array.from({ length: 30 }, (_, k) => thisYear - 1 - k)
