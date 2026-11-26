// The alfalfa growth and cutting planner (`/tools/alfalfa`, Phase 7 track 5 P1, D129): how far alfalfa has grown
// since its last cut (`/models/alfalfa-growth/run` with `biofix`, extended by past years' weather) and a season's
// cutting plan (`/models/alfalfa-growth/plan`). Pure functions over the API's answers, asked in °F (`units=us`) and
// converted only for display: what the page reads, the sentences, the plan's edits and the two charts.
//
//   const since = sinceCut(runBody, today)          // growth since the cut, and when the window comes
//   sinceCutWords(since, units)                       // { headline, details }
//   sinceCutOption({ since, units, palette, today })  // GDD since the cut over the cutting window
//   const plan = parsePlan(planBody)                  // the plan's cuts, fall check and days
//   cutLine(plan, k, units), seasonWords(plan, units), fallWords(plan, units)
//   planOption({ plan, units, palette, today })       // the sawtooth over the killing-freeze chance

import type { TableResponse } from '@/types/api'

import type { ChartTable } from '../charts/ChartCard.svelte'
import type { EChartsCoreOption } from '../charts/echarts'
import { band, forecastBand, isForecast, lineStyle } from '../charts/kinds'
import { baseOption, type Palette } from '../charts/palette'
import { temperatureText } from '../climate/words'
import { addDays, formatDate } from '../dates'
import { andList, monthDay } from '../models/format'
import { tableRows, type Day, type Table } from '../tableRows'
import { formatNumber, type Units } from '../units'
import { summaryYears, type Period, type PeriodYears } from '../climate/periods'

// --- Settings --------------------------------------------------------------------------------------------------

/** The model's cutting window and Newell's fall rule, GDD (°F·d, base 41 °F, upper 86 °F); the API's own
 * numbers (`meta.summary.stages`, `plan.thresholds`) win where it gives them */
export const WINDOW_F = { from: 900, until: 1100 } as const
export const FALL_F = { under: 360, over: 900 } as const
export const KILLING_FREEZE_F = 24

/** Schedule by an interval (800–1,200 GDD, 1,000 by default) or a number of cuts (2–6 here; the API takes 1–8) */
export const INTERVAL_F = { min: 800, max: 1200, step: 50, default: 1000 } as const
export const COUNTS = [2, 3, 4, 5, 6] as const
export const DEFAULT_COUNT = 4
export const MAX_CUTS = 8

export type ScheduleBy = 'interval' | 'count'

/** GDD (stored in °F·d) in the reader's units, in a sentence: "987 GDD", or "548 °C·d" in metric */
export function gddText(fahrenheit: number | null | undefined, units: Units): string {
  if (fahrenheit === null || fahrenheit === undefined) return '—'
  if (units.system === 'metric') return units.format('degF_day', fahrenheit, { digits: 0 })
  return `${formatNumber(fahrenheit, 0)} GDD`
}

/** "900–1,100 GDD", or "500–611 °C·d" */
export function windowText(window: { from: number; until: number }, units: Units): string {
  const from = units.format('degF_day', window.from, { digits: 0, unit: false })
  const until = units.format('degF_day', window.until, { digits: 0, unit: false })
  return `${from}–${until} ${units.system === 'metric' ? units.label('degF_day') : 'GDD'}`
}

/** "June 7" for "2026-06-07" */
export const dayName = (iso: string): string => monthDay(iso.slice(5, 10))

// --- Since the last cut -------------------------------------------------------------------------------------------

/** A threshold reached through the forecast: the day, and whether it was observed or is forecast */
export type Reached = { date: string; forecast: boolean }

/** A threshold past years' weather says is still ahead: the 10th, 50th and 90th percentile dates, and in how many
 * of the years it was reached by the end of the year */
export type Expected = { p10: string | null; p50: string | null; p90: string | null; reached: number; of: number }

export type SinceCut = {
  table: Table
  /** The day counting starts: the cut's date, or January 1 for spring growth */
  from: string
  spring: boolean
  /** The latest total through today, and its day */
  total: number | null
  asOf: string | null
  window: { from: number; until: number }
  entered: Reached | null
  passed: Reached | null
  /** Set only when the threshold isn't reached through the forecast and a projection ran */
  enterExpected: Expected | null
  passExpected: Expected | null
  warnings: string[]
}

type Milestones = {
  name?: string
  reached?: number
  of?: number
  p10?: string | null
  p50?: string | null
  p90?: string | null
}[]

const recordOf = (value: unknown) => (value && typeof value === 'object' ? (value as Record<string, unknown>) : {})

/** The stage thresholds the run gives (`meta.summary.stages`, in the request's units: °F·d here) */
function stageThreshold(summary: Record<string, unknown>, code: string, fallback: number): number {
  const stages = (summary.stages ?? []) as { code?: string; threshold?: number }[]
  const found = stages.find((stage) => stage.code === code)
  return typeof found?.threshold === 'number' ? found.threshold : fallback
}

function firstReaching(days: Day[], threshold: number): Reached | null {
  for (const day of days) {
    if (day.kind === 'projection') break
    const value = day.values.gdd_total
    if (value != null && value >= threshold) return { date: day.date, forecast: isForecast(day) }
  }
  return null
}

function expected(milestones: Milestones, code: string): Expected | null {
  const found = milestones.find((m) => m.name === code)
  if (!found || typeof found.of !== 'number' || found.of === 0) return null
  return {
    p10: found.p10 ?? null,
    p50: found.p50 ?? null,
    p90: found.p90 ?? null,
    reached: found.reached ?? 0,
    of: found.of,
  }
}

/** `/models/alfalfa-growth/run`'s answer (asked with `units=us`, `projection=true`) as the section reads it */
export function sinceCut(body: Pick<TableResponse, 'meta' | 'data'>, today: string): SinceCut {
  const table = tableRows(body)
  const summary = recordOf(body.meta.summary)
  const request = recordOf(body.meta.request)
  const from = typeof request.biofix === 'string' ? request.biofix : (table.days[0]?.date ?? today)
  const window = {
    from: stageThreshold(summary, 'Cut', WINDOW_F.from),
    until: stageThreshold(summary, 'Late', WINDOW_F.until),
  }
  const seen = table.days.filter(
    (day) => day.kind !== 'projection' && day.date <= today && day.values.gdd_total != null,
  )
  const latest = seen.at(-1) ?? null
  const entered = firstReaching(table.days, window.from)
  const passed = firstReaching(table.days, window.until)
  const milestones = (recordOf(summary.projection).milestones ?? []) as Milestones
  return {
    table,
    from,
    spring: from.slice(5) === '01-01',
    total: latest?.values.gdd_total ?? null,
    asOf: latest?.date ?? null,
    window,
    entered,
    passed,
    enterExpected: entered ? null : expected(milestones, 'Cut'),
    passExpected: passed ? null : expected(milestones, 'Late'),
    warnings: (body.meta.warnings ?? []).filter((w) => !/nothing to project/.test(w)),
  }
}

/** "about June 28 (likely between June 25 and July 2)" */
function expectedText(e: Expected): string | null {
  if (!e.p50 || e.reached * 2 < e.of) return null
  const range = e.p10 && e.p90 && e.p10 !== e.p90 ? ` (likely between ${dayName(e.p10)} and ${dayName(e.p90)})` : ''
  return `about ${dayName(e.p50)}${range}`
}

/** The section's answer in words: the total since the cut, then where it stands against the cutting window */
export function sinceCutWords(s: SinceCut, units: Units): { headline: string; details: string[] } {
  const since = s.spring ? `since January 1` : `since the cut on ${dayName(s.from)}`
  const through = s.asOf ? ` (through ${dayName(s.asOf)})` : ''
  const headline =
    s.total === null
      ? `We have no degree days for this location ${since} yet.`
      : `Alfalfa here has had ${gddText(s.total, units)} ${since}${through}.`
  const start = gddText(s.window.from, units)
  const end = gddText(s.window.until, units)
  const details: string[] = []
  // "reached the cutting window (900 GDD) on September 12", or "is forecast to reach … on …"
  const reachedText = (r: Reached, verb: string, future: string, what: string) =>
    `${r.forecast ? `is forecast to ${future}` : verb} ${what} on ${dayName(r.date)}`
  if (s.passed) {
    const entered = s.entered
      ? `${reachedText(s.entered, 'reached', 'reach', `the cutting window (${start})`)} and `
      : ''
    details.push(
      `It ${entered}${reachedText(s.passed, 'passed', 'pass', `${end}, the end of the window,`)}. Past the window, forage quality declines as the crop matures.`,
    )
  } else if (s.entered) {
    const pass = s.passExpected ? expectedText(s.passExpected) : null
    details.push(
      s.entered.forecast
        ? `It is forecast to reach the cutting window (${start}) on ${dayName(s.entered.date)}.`
        : `It reached the cutting window (${start}) on ${dayName(s.entered.date)}, so it is ready to cut.`,
    )
    if (pass)
      details.push(
        `From past years’ weather after the forecast, it is expected to pass ${end}, the end of the window, ${pass}.`,
      )
  } else {
    const e = s.enterExpected
    const enter = e ? expectedText(e) : null
    if (enter) {
      details.push(
        `From past years’ weather after the forecast, it is expected to reach the cutting window (${start}) ${enter}.`,
      )
      if (e && e.reached < e.of)
        details.push(`It reached it before the end of the year in ${e.reached} of ${e.of} past years’ weather.`)
    } else if (e) {
      details.push(
        e.reached === 0
          ? `In none of ${e.of} past years’ weather after the forecast does it reach the cutting window (${start}) before the end of the year.`
          : `It reaches the cutting window (${start}) before the end of the year in only ${e.reached} of ${e.of} past years’ weather after the forecast.`,
      )
    } else {
      details.push(`It hasn’t reached the cutting window (${start}) through the forecast.`)
    }
  }
  return { headline, details }
}

const rounded = (value: number | null) => (value === null ? null : Number(value.toFixed(2)))

/** GDD since the cut: observed and forecast solid, the projection's middle dashed over its P10–P90 band, the
 * cutting window as a band across the chart, a Today line and the forecast shaded */
export function sinceCutOption({
  since,
  units,
  palette,
  today,
}: {
  since: SinceCut
  units: Units
  palette: Palette
  today: string
}): EChartsCoreOption {
  const base = baseOption(palette)
  const days = since.table.days
  const dates = days.map((day) => day.date)
  const shown = (day: Day, column: string) => rounded(units.toDisplay('degF_day', day.values[column] ?? null))
  const values = days.map((day) => shown(day, 'gdd_total'))
  const projected = days.map((day) => day.kind === 'projection')
  const firstProjected = projected.indexOf(true)
  const color = palette.degreeDays
  const { shading, label: forecastLabel } = forecastBand({ dates, days, grids: 1, axisOffset: 1, palette })
  const [lo, hi] = [since.window.from, since.window.until].map((v) => units.toDisplay('degF_day', v) as number)
  const marks = dates.includes(today)
    ? [
        {
          xAxis: today,
          lineStyle: { color: palette.ink, type: 'dashed', width: 1, opacity: 0.6 },
          label: { formatter: 'Today', position: 'insideEndTop', color: palette.inkMuted, fontSize: 10 },
        },
      ]
    : []
  const series: object[] = [
    {
      id: 'gdd',
      name: 'GDD since the cut',
      type: 'line',
      symbol: 'none',
      connectNulls: false,
      lineStyle: lineStyle(color),
      itemStyle: { color },
      data: values.map((v, i) => (projected[i] ? null : v)),
      markLine: { silent: true, symbol: 'none', data: marks },
      markArea: {
        silent: true,
        itemStyle: { color, opacity: 0.12 },
        label: { color: palette.inkMuted, fontSize: 10, position: 'insideTopLeft' },
        data: [[{ yAxis: lo, name: 'Cutting window' }, { yAxis: hi }]],
      },
    },
  ]
  if (forecastLabel) series.push({ id: 'forecast-label', type: 'line', data: [], markArea: forecastLabel })
  if (firstProjected >= 0) {
    series.push({
      id: 'gdd-projection',
      name: 'Projection (middle of past years)',
      type: 'line',
      symbol: 'none',
      lineStyle: lineStyle(color, 'projection'),
      itemStyle: { color },
      data: values.map((v, i) => (i >= firstProjected - 1 ? v : null)),
    })
    series.push(
      ...band({
        id: 'gdd',
        lower: days.map((day, i) => (projected[i] ? shown(day, 'gdd_total_p10') : null)),
        upper: days.map((day, i) => (projected[i] ? shown(day, 'gdd_total_p90') : null)),
        color: palette.projection,
      }),
    )
  }
  const unit = units.label('degF_day')
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number }[]
        const day = days[list[0]?.dataIndex ?? -1]
        if (!day) return ''
        const kind = day.kind === 'projection' ? ' (projection)' : isForecast(day) ? ' (forecast)' : ''
        let text = `${units.format('degF_day', day.values.gdd_total, { digits: 0 })}`
        if (day.kind === 'projection' && day.values.gdd_total_p10 != null)
          text += ` (P10–P90 ${units.format('degF_day', day.values.gdd_total_p10, { digits: 0, unit: false })} to ${units.format('degF_day', day.values.gdd_total_p90, { digits: 0 })})`
        return `<strong>${formatDate(day.date, { weekday: true })}${kind}</strong><br>GDD since the cut: ${text}`
      },
    },
    grid: [{ left: 48, right: 12, top: 16, bottom: 26 }],
    xAxis: [
      {
        type: 'category',
        data: dates,
        axisLabel: { ...base.axisLabel, formatter: (date: string) => formatDate(date) },
        axisLine: base.axisLine,
      },
      ...shading.xAxis,
    ],
    yAxis: [
      {
        type: 'value',
        min: 0,
        name: `GDD (${unit})`,
        nameTextStyle: { color: palette.inkMuted, fontSize: 10, align: 'left' },
        max: (extent: { max: number }) => (extent.max < hi * 1.05 ? Math.ceil((hi * 1.05) / 100) * 100 : undefined),
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      ...shading.yAxis,
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, ...shading.xAxisIndexes] }],
    series: [...series, ...shading.series],
  }
}

/** "Summary and data"'s table for the section's chart, newest first */
export function sinceCutTable(since: SinceCut, units: Units): ChartTable {
  const unit = units.label('degF_day')
  const projection = since.table.days.some((day) => day.kind === 'projection')
  const value = (v: number | null | undefined) =>
    v == null ? null : units.format('degF_day', v, { digits: 0, unit: false })
  return {
    columns: [`GDD since the cut (${unit})`, ...(projection ? ['10th percentile', '90th percentile'] : [])],
    rows: since.table.days
      .map((day) => ({
        date: day.date,
        forecast: isForecast(day) || day.kind === 'projection',
        values: [
          value(day.values.gdd_total),
          ...(projection ? [value(day.values.gdd_total_p10), value(day.values.gdd_total_p90)] : []),
        ],
      }))
      .toReversed(),
  }
}

// --- The season plan ----------------------------------------------------------------------------------------------

export type CutStatus = 'early' | 'window' | 'late'
export type Basis = 'observed' | 'typical' | 'none'

export type PlanCut = { date: string; held: boolean; gdd: number; days: number; status: CutStatus; projected: boolean }

export type PlanFall = {
  lastCut: string | null
  years: number
  under: number
  over: number
  between: number
  beforeCut: number
  typicalFreeze: string | null
  typicalRegrowth: number | null
  observedFreeze: string | null
  observedRegrowth: number | null
}

export type PlanDay = {
  date: string
  /** observed, partial or forecast for this year's weather; normal where the plan uses the normal */
  kind: string | null
  gdd: number | null
  sinceCut: number | null
  killChance: number | null
  cut: boolean
}

export type Plan = {
  year: number
  springFreeze: { date: string | null; basis: Basis }
  seasonEnd: { date: string | null; basis: Basis }
  interval: number | null
  count: number | null
  cuts: PlanCut[]
  fall: PlanFall | null
  thresholds: { cutFrom: number; cutUntil: number; fallUnder: number; fallOver: number; killingFreeze: number }
  days: PlanDay[]
  years: PeriodYears | null
  daysNormal: number
  warnings: string[]
}

const num = (value: unknown): number | null => (typeof value === 'number' && Number.isFinite(value) ? value : null)
const str = (value: unknown): string | null => (typeof value === 'string' ? value : null)
const basisOf = (value: unknown): Basis => (value === 'observed' || value === 'typical' ? value : 'none')

/** `/models/alfalfa-growth/plan`'s answer (asked with `units=us`) as the page reads it */
export function parsePlan(body: Pick<TableResponse, 'meta' | 'data'>): Plan {
  const summary = recordOf(body.meta.summary)
  const plan = recordOf(summary.plan)
  const request = recordOf(body.meta.request)
  const spring = recordOf(plan.spring_freeze)
  const end = recordOf(plan.season_end)
  const fall = plan.fall ? recordOf(plan.fall) : null
  const t = recordOf(plan.thresholds)
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, unknown[]>
  const dates = (data.date ?? []) as string[]
  const column = (name: string) => (data[name] ?? []) as unknown[]
  const [kind, gdd, since, chance, cut] = ['kind', 'gdd', 'gdd_since_cut', 'kill_chance', 'cut'].map(column)
  return {
    year: num(request.year) ?? Number((dates[0] ?? '').slice(0, 4)),
    springFreeze: { date: str(spring.date), basis: basisOf(spring.basis) },
    seasonEnd: { date: str(end.date), basis: basisOf(end.basis) },
    interval: num(plan.interval),
    count: num(plan.count),
    cuts: ((plan.cuts ?? []) as Record<string, unknown>[]).map((c) => ({
      date: String(c.date),
      held: c.held === true,
      gdd: num(c.gdd) ?? 0,
      days: num(c.days) ?? 0,
      status: (c.status === 'early' || c.status === 'late' ? c.status : 'window') as CutStatus,
      projected: c.projected === true,
    })),
    fall: fall
      ? {
          lastCut: str(fall.last_cut),
          years: num(fall.years) ?? 0,
          under: num(fall.under) ?? 0,
          over: num(fall.over) ?? 0,
          between: num(fall.between) ?? 0,
          beforeCut: num(fall.before_cut) ?? 0,
          typicalFreeze: str(fall.typical_freeze),
          typicalRegrowth: num(fall.typical_regrowth),
          observedFreeze: str(fall.observed_freeze),
          observedRegrowth: num(fall.observed_regrowth),
        }
      : null,
    thresholds: {
      cutFrom: num(t.cut_from) ?? WINDOW_F.from,
      cutUntil: num(t.cut_until) ?? WINDOW_F.until,
      fallUnder: num(t.fall_under) ?? FALL_F.under,
      fallOver: num(t.fall_over) ?? FALL_F.over,
      killingFreeze: num(t.killing_freeze) ?? KILLING_FREEZE_F,
    },
    days: dates.map((date, i) => ({
      date,
      kind: str(kind[i]),
      gdd: num(gdd[i]),
      sinceCut: num(since[i]),
      killChance: num(chance[i]),
      cut: cut[i] === true,
    })),
    years: summaryYears(summary),
    daysNormal: num(summary.days_normal) ?? 0,
    warnings: body.meta.warnings ?? [],
  }
}

/** The plan request's query, without the place: scheduled by interval or count with any held cuts, or the reader's
 * own dates checked as they are */
export function planQuery({
  year,
  thisYear,
  period,
  by,
  target,
  cuts,
  held,
}: {
  year: number
  thisYear: number
  period: Period
  by: ScheduleBy
  target: number | null
  cuts: string[]
  held: string[]
}): Record<string, string | number | string[] | undefined> {
  const query: Record<string, string | number | string[] | undefined> = {
    units: 'us',
    year: year === thisYear ? undefined : year,
    period: period === 'last30' ? undefined : period,
  }
  if (cuts.length) {
    query.cuts = cuts
    const kept = held.filter((date) => cuts.includes(date))
    if (kept.length) query.held = kept
    return query
  }
  if (by === 'count') query.count = target ?? DEFAULT_COUNT
  else query.interval = target ?? INTERVAL_F.default
  if (held.length) query.held = held
  return query
}

/** A plan's cuts and holds after one edit. Every edit works on the plan's own dates, so the plan is then checked
 * as it stands (`cuts=`) rather than scheduled again: a date that's changed, held or removed leaves the others
 * where they are. Dates are kept sorted and distinct; a hold follows its cut's date. */
export type CutEdit =
  { kind: 'date'; index: number; date: string } | { kind: 'hold'; index: number } | { kind: 'remove'; index: number }

export function editCuts(cuts: PlanCut[], edit: CutEdit): { cuts: string[]; held: string[] } {
  const rows = cuts.map((c) => ({ date: c.date, held: c.held }))
  const row = rows[edit.index]
  if (!row) return { cuts: rows.map((r) => r.date), held: rows.filter((r) => r.held).map((r) => r.date) }
  if (edit.kind === 'date') row.date = edit.date
  else if (edit.kind === 'hold') row.held = !row.held
  else rows.splice(edit.index, 1)
  const byDate = new Map<string, boolean>()
  for (const r of rows) byDate.set(r.date, (byDate.get(r.date) ?? false) || r.held)
  const dates = [...byDate.keys()].sort()
  return { cuts: dates, held: dates.filter((d) => byDate.get(d)) }
}

/** Where the season starts and where cuts are scheduled through, and why */
export function seasonWords(plan: Plan, units: Units): string {
  const freeze = `killing freeze (${temperatureText(plan.thresholds.killingFreeze, units)} or colder)`
  const start =
    plan.springFreeze.basis === 'observed' && plan.springFreeze.date
      ? `The season counts from this year’s last spring ${freeze}, on ${dayName(plan.springFreeze.date)}.`
      : plan.springFreeze.basis === 'typical' && plan.springFreeze.date
        ? `Spring hasn’t yet reached the typical date of the last spring ${freeze}, so the season counts from that date, ${dayName(plan.springFreeze.date)}.`
        : `There was no spring ${freeze} this year, so the season counts from January 1.`
  const end =
    plan.seasonEnd.basis === 'observed' && plan.seasonEnd.date
      ? `Cuts are scheduled through this year’s first fall killing freeze, on ${dayName(plan.seasonEnd.date)}.`
      : plan.seasonEnd.basis === 'typical' && plan.seasonEnd.date
        ? `Cuts are scheduled through ${dayName(plan.seasonEnd.date)}, the date by which 1 year in 10 has had its first fall killing freeze.`
        : `Cuts are scheduled through December 31.`
  return `${start} ${end}`
}

const STATUS_WORDS: Record<CutStatus, string> = {
  early: 'before the cutting window',
  window: 'in the cutting window',
  late: 'past the cutting window',
}

/** "Cut 2, July 11: 991 GDD in 34 days since cut 1, in the cutting window." with held and projected noted */
export function cutLine(plan: Plan, index: number, units: Units): string {
  const cut = plan.cuts[index]
  if (!cut) return ''
  const since = index === 0 ? 'since the season began' : `since cut ${index}`
  const days = `${cut.days} ${cut.days === 1 ? 'day' : 'days'}`
  const notes = [cut.held ? 'Held in place.' : '', cut.projected ? 'Projected: it rests partly on the normal.' : '']
  return [
    `Cut ${index + 1}, ${dayName(cut.date)}: ${gddText(cut.gdd, units)} in ${days} ${since}, ${STATUS_WORDS[cut.status]}.`,
    ...notes,
  ]
    .filter(Boolean)
    .join(' ')
}

/** "1 year", "5 years", "no years" */
const yearsText = (n: number) => (n === 0 ? 'no years' : `${n} ${n === 1 ? 'year' : 'years'}`)

/** The fall rule and how the plan's last cut fares against each of the period's years */
export function fallWords(plan: Plan, units: Units): { rule: string; check: string[] } {
  const t = plan.thresholds
  const rule = `Before winter, alfalfa needs either too little regrowth after its last cut to draw down the reserves in its roots, under ${gddText(t.fallUnder, units)}, or enough to rebuild them, over ${gddText(t.fallOver, units)}, before the first fall killing freeze (${temperatureText(t.killingFreeze, units)} or colder). Regrowth between the two leaves the stand weaker going into winter.`
  const fall = plan.fall
  if (!fall || !fall.lastCut || fall.years === 0) return { rule, check: [] }
  const period = plan.years ? ` from ${plan.years.first} to ${plan.years.last}` : ''
  const parts = [
    `under ${gddText(t.fallUnder, units)} in ${yearsText(fall.under)}`,
    `over ${gddText(t.fallOver, units)} in ${yearsText(fall.over)}`,
    `between them in ${yearsText(fall.between)}`,
  ]
  const check = [
    `With the last cut on ${dayName(fall.lastCut)}, the regrowth before the first fall killing freeze, in each of the ${fall.years} years${period}, was ${andList(parts)}${fall.beforeCut ? `; in ${yearsText(fall.beforeCut)} the freeze came on or before the cut` : ''}.`,
  ]
  if (fall.typicalFreeze)
    check.push(
      `In a typical year the killing freeze comes about ${dayName(fall.typicalFreeze)}${fall.typicalRegrowth !== null ? `, after ${gddText(fall.typicalRegrowth, units)} of regrowth` : ''}.`,
    )
  if (fall.observedFreeze)
    check.push(
      `This year it came on ${dayName(fall.observedFreeze)}${fall.observedRegrowth !== null ? `, after ${gddText(fall.observedRegrowth, units)} of regrowth` : ''}.`,
    )
  return { rule, check }
}

/** The days the plan's chart shows: from two weeks before the season starts (March 15 at the latest) to three weeks
 * after its end or this year's fall killing freeze, within the year */
export function planSpan(plan: Plan): [number, number] {
  const days = plan.days
  if (!days.length) return [0, -1]
  const year = plan.year
  const spring =
    plan.springFreeze.date && plan.springFreeze.date < `${year}-03-15` ? plan.springFreeze.date : `${year}-03-15`
  const ends = [plan.seasonEnd.date, plan.fall?.observedFreeze, plan.cuts.at(-1)?.date].filter((d): d is string => !!d)
  const end = ends.length ? ends.sort().at(-1)! : `${year}-11-30`
  const first = addDays(spring, -14)
  const last = addDays(end, 21)
  let lo = days.findIndex((d) => d.date >= first)
  let hi = days.findLastIndex((d) => d.date <= last)
  if (lo < 0) lo = 0
  if (hi < 0) hi = days.length - 1
  return [lo, hi]
}

const kindWords = (kind: string | null) =>
  kind === 'normal' ? ' (normal)' : kind === 'forecast' || kind === 'partial' ? ' (forecast)' : ''

/** The plan as a stacked chart on one time axis: GDD since the last cut, a sawtooth falling to zero at each cut,
 * with the cutting window as a band and each cut marked (held cuts filled), this year's weather solid and the
 * normal dashed; under it, the chance of a killing freeze */
export function planOption({
  plan,
  units,
  palette,
  today,
}: {
  plan: Plan
  units: Units
  palette: Palette
  today: string
}): EChartsCoreOption {
  const base = baseOption(palette)
  const [lo, hi] = planSpan(plan)
  const days = plan.days.slice(lo, hi + 1)
  const dates = days.map((d) => d.date)
  const shown = (v: number | null) => rounded(units.toDisplay('degF_day', v))
  const values = days.map((d) => shown(d.sinceCut))
  const normal = days.map((d) => d.kind === 'normal')
  const firstNormal = normal.indexOf(true)
  const color = palette.degreeDays
  const [windowLo, windowHi] = [plan.thresholds.cutFrom, plan.thresholds.cutUntil].map((v) => shown(v) as number)
  const forecastAt = days.findIndex((d) => d.kind === 'forecast' || d.kind === 'partial')
  const forecastEnd = days.findLastIndex((d) => d.kind === 'forecast' || d.kind === 'partial')
  const unit = units.label('degF_day')
  const mark = (date: string, label: string, show: boolean, dashed = false) => ({
    xAxis: date,
    lineStyle: dashed
      ? { color: palette.ink, type: 'dashed', width: 1, opacity: 0.6 }
      : { color: palette.inkMuted, type: 'dotted', width: 1.5 },
    label: show
      ? { formatter: label, position: 'insideEndTop', color: palette.inkMuted, fontSize: 10 }
      : { show: false },
  })
  const guides = (top: boolean) => [
    ...(dates.includes(today) ? [mark(today, 'Today', top, true)] : []),
    ...(plan.seasonEnd.date && dates.includes(plan.seasonEnd.date) && plan.seasonEnd.basis !== 'none'
      ? [mark(plan.seasonEnd.date, 'Season end', top)]
      : []),
  ]
  // Each cut as a marker on its day (a line series of lone points: the charts' ECharts build has no scatter)
  const cutPoints = days.map((day) => {
    const k = plan.cuts.findIndex((cut) => cut.date === day.date)
    if (k < 0) return null
    const cut = plan.cuts[k]
    return {
      value: shown(day.sinceCut ?? cut.gdd),
      symbol: cut.held ? 'diamond' : 'emptyDiamond',
      symbolSize: 12,
      itemStyle: { color: cut.held ? palette.ink : palette.surface, borderColor: palette.ink, borderWidth: 1.5 },
      label: { show: true, formatter: `Cut ${k + 1}`, position: 'top', color: palette.ink, fontSize: 10 },
    }
  })
  const series: object[] = [
    {
      id: 'since-cut',
      name: 'This year’s weather',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      symbol: 'none',
      connectNulls: false,
      lineStyle: lineStyle(color),
      itemStyle: { color },
      data: values.map((v, i) => (normal[i] ? null : v)),
      markLine: { silent: true, symbol: 'none', data: guides(true) },
      markArea: {
        silent: true,
        itemStyle: { color, opacity: 0.12 },
        label: { color: palette.inkMuted, fontSize: 10, position: 'insideTopLeft' },
        data: [[{ yAxis: windowLo, name: 'Cutting window' }, { yAxis: windowHi }]],
      },
    },
    {
      id: 'since-cut-normal',
      name: 'Normal',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      symbol: 'none',
      connectNulls: false,
      lineStyle: lineStyle(color, 'projection'),
      itemStyle: { color },
      // From the last day of this year's weather, so the line doesn't break
      data: values.map((v, i) => (firstNormal >= 0 && (normal[i] || i === firstNormal - 1) ? v : null)),
    },
    {
      id: 'cuts',
      name: 'Cuts',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      showSymbol: true,
      connectNulls: false,
      lineStyle: { width: 0 },
      itemStyle: { color: palette.ink },
      data: cutPoints,
      z: 5,
    },
    {
      id: 'kill-chance',
      name: 'Chance of a killing freeze',
      type: 'line',
      xAxisIndex: 1,
      yAxisIndex: 1,
      symbol: 'none',
      lineStyle: { width: 2, color: palette.temperature.min },
      itemStyle: { color: palette.temperature.min },
      data: days.map((d) => d.killChance),
      markLine: { silent: true, symbol: 'none', data: guides(false) },
    },
  ]
  if (forecastAt >= 0)
    series.push({
      id: 'forecast-shading',
      type: 'line',
      xAxisIndex: 0,
      yAxisIndex: 0,
      data: [],
      markArea: {
        silent: true,
        itemStyle: { color: palette.inkMuted, opacity: 0.08 },
        label: { show: true, position: 'insideTop', color: palette.inkMuted, fontSize: 10, formatter: 'Forecast' },
        data: [[{ xAxis: dates[forecastAt] }, { xAxis: dates[forecastEnd] }]],
      },
    })
  const titles = [
    { text: `GDD since the last cut (${unit})`, top: 0 },
    {
      text: `Chance of a killing freeze, ${temperatureText(plan.thresholds.killingFreeze, units)} or colder (%)`,
      top: 232,
    },
  ].map((t) => ({ ...t, left: 0, textStyle: { fontSize: 11, fontWeight: 'normal', color: palette.inkMuted } }))
  const xAxis = (grid: number) => ({
    type: 'category',
    data: dates,
    gridIndex: grid,
    axisLabel: grid === 1 ? { ...base.axisLabel, formatter: (date: string) => formatDate(date) } : { show: false },
    axisTick: { show: grid === 1 },
    axisLine: base.axisLine,
  })
  return {
    animation: base.animation,
    textStyle: base.textStyle,
    title: titles,
    legend: {
      top: 14,
      left: 0,
      data: ['This year’s weather', 'Normal', 'Cuts'],
      textStyle: { color: palette.inkMuted, fontSize: 10 },
      itemWidth: 14,
      itemHeight: 8,
      selectedMode: false,
    },
    tooltip: {
      ...base.tooltip,
      formatter: (params: unknown) => {
        const list = (Array.isArray(params) ? params : [params]) as { dataIndex: number; seriesId?: string }[]
        const first = list.find((p) => p.seriesId !== 'cuts') ?? list[0]
        const day = days[first?.dataIndex ?? -1]
        return day ? planTooltip(plan, day, units) : ''
      },
    },
    axisPointer: { link: [{ xAxisIndex: 'all' }] },
    grid: [
      { left: 48, right: 12, top: 36, height: 180 },
      { left: 48, right: 12, top: 252, height: 70 },
    ],
    xAxis: [xAxis(0), xAxis(1)],
    yAxis: [
      {
        type: 'value',
        gridIndex: 0,
        min: 0,
        max: (extent: { max: number }) =>
          extent.max < windowHi * 1.08 ? Math.ceil((windowHi * 1.08) / 100) * 100 : undefined,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
      {
        type: 'value',
        gridIndex: 1,
        min: 0,
        max: 100,
        interval: 50,
        axisLabel: base.axisLabel,
        splitLine: base.splitLine,
      },
    ],
    dataZoom: [{ type: 'inside', xAxisIndex: [0, 1] }],
    series,
  }
}

/** The plan chart's height, to match planOption's grids */
export const PLAN_CHART_HEIGHT = '350px'

function planTooltip(plan: Plan, day: PlanDay, units: Units): string {
  const k = plan.cuts.findIndex((c) => c.date === day.date)
  const lines = [`<strong>${formatDate(day.date, { weekday: true })}${kindWords(day.kind)}</strong>`]
  if (day.sinceCut !== null)
    lines.push(`GDD since the last cut: ${units.format('degF_day', day.sinceCut, { digits: 0 })}`)
  if (k >= 0) lines.push(`<strong>Cut ${k + 1}</strong>${plan.cuts[k].held ? ' (held)' : ''}`)
  if (day.killChance !== null) {
    const spring = day.date.slice(5) < '07-01'
    lines.push(`Chance of a killing freeze ${spring ? 'after' : 'by'} this date: ${Math.round(day.killChance)}%`)
  }
  return lines.join('<br>')
}

/** The plan chart in words: its text alternative and summary */
export function planSummary(plan: Plan, units: Units): string {
  const lines = plan.cuts.map((_, k) => cutLine(plan, k, units))
  return [seasonWords(plan, units), ...lines].join(' ')
}

/** "Summary and data"'s table for the plan, newest first */
export function planTable(plan: Plan, units: Units): ChartTable {
  const unit = units.label('degF_day')
  const value = (v: number | null) => (v === null ? null : units.format('degF_day', v, { digits: 0, unit: false }))
  const [lo, hi] = planSpan(plan)
  return {
    columns: ['Weather', `GDD (${unit})`, `GDD since the last cut (${unit})`, 'Cut', 'Killing freeze chance (%)'],
    rows: plan.days
      .slice(lo, hi + 1)
      .map((day) => ({
        date: day.date,
        forecast: day.kind === 'forecast' || day.kind === 'partial',
        values: [
          day.kind === 'normal' ? 'Normal' : day.kind === 'observed' ? 'Observed' : day.kind ? 'Forecast' : null,
          value(day.gdd),
          value(day.sinceCut),
          day.cut ? `Cut ${plan.cuts.findIndex((c) => c.date === day.date) + 1}` : null,
          day.killChance === null ? null : String(Math.round(day.killChance)),
        ],
      }))
      .toReversed(),
  }
}
