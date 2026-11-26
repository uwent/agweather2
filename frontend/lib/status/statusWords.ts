// The data status page (/status, Phase 7 step 7.2) in words: `/api/v2/status`'s answer read against each source's
// usual delay (web.status.SOURCE_LAG, sent as the page's `sources`). Times are on the grid's clock, Central Standard
// Time all year (D74), as every "data through" line on the site.

import { cstTime } from '@/lib/dataStatus'
import { andList } from '@/lib/models/format'
import type { StatusSource } from '@/types'
import type { StatusData } from '@/types/api'

const HOUR_MS = 3_600_000

export type SourceState = 'on-time' | 'late' | 'none'

export type SourceRow = {
  id: string
  name: string
  url: string
  provides: string
  /** "10 p.m. CST, Nov 25", or null when the source has sent nothing */
  newest: string | null
  /** "within 4 hours" */
  normally: string
  state: SourceState
  /** "On time", "Late" or "No data" */
  stateLabel: string
}

export type Headline = { level: 'ok' | 'late' | 'down'; text: string }

/** "4 hours", "1 hour", "7 days" */
export function spanText(hours: number): string {
  if (hours >= 48 && hours % 24 === 0) return `${hours / 24} days`
  if (hours === 1) return '1 hour'
  return `${Math.round(hours)} hours`
}

/** How long ago an instant was, roughly: "45 minutes", "6 hours", "3 days" */
export function agoText(iso: string, now: Date): string {
  const hours = (now.getTime() - new Date(iso).getTime()) / HOUR_MS
  if (hours < 1) {
    const minutes = Math.max(1, Math.round(hours * 60))
    return minutes === 1 ? '1 minute' : `${minutes} minutes`
  }
  if (hours < 48) return Math.round(hours) === 1 ? '1 hour' : `${Math.round(hours)} hours`
  return `${Math.round(hours / 24)} days`
}

const STATE_LABELS: Record<SourceState, string> = { 'on-time': 'On time', late: 'Late', none: 'No data' }

/** Each source with its newest hour and whether it's later than it normally runs */
export function sourceRows(report: StatusData, sources: StatusSource[], now: Date): SourceRow[] {
  return sources.map((source) => {
    const newest = report.archive.last_hour_by_source[source.id] ?? null
    const state: SourceState =
      newest === null
        ? 'none'
        : now.getTime() - new Date(newest).getTime() > source.normal_lag_hours * HOUR_MS
          ? 'late'
          : 'on-time'
    return {
      id: source.id,
      name: source.name,
      url: source.url,
      provides: source.provides,
      newest: newest === null ? null : cstTime(newest),
      normally: `within ${spanText(source.normal_lag_hours)}`,
      state,
      stateLabel: STATE_LABELS[state],
    }
  })
}

/** The short name a source goes by in a sentence: "URMA" from "URMA (Unrestricted Mesoscale Analysis), NOAA" */
export function shortName(name: string): string {
  return name.split(/[ ,(]/)[0]
}

// What a late source leaves out, in a sentence
const SOURCE_KINDS: Record<string, string> = {
  urma: 'temperature, humidity, wind and precipitation',
  rtma: 'temperature, humidity, wind and precipitation',
  hrrr: 'solar radiation',
  era5land: 'soil temperature, soil moisture and snow depth',
  ifs: 'soil temperature, soil moisture and snow depth',
}

/** The page's first sentence: everything current, or what's late and what that means */
export function headline(report: StatusData, rows: SourceRow[]): Headline {
  const sent = rows.filter((r) => r.state !== 'none')
  if (!sent.length) return { level: 'down', text: 'We have no weather data yet.' }
  const forecast = report.forecast
  const parts: string[] = []
  // A provisional source late while its replacement is current isn't worth the headline: RTMA fills URMA's newest
  // hours, and IFS ERA5-Land's newest days, so only both of a pair being late leaves a gap readers would see
  const late = rows.filter((r) => r.state === 'late')
  const lateIds = new Set(late.map((r) => r.id))
  const covering: Record<string, string> = { urma: 'rtma', era5land: 'ifs' }
  const visible = late.filter((r) => !(covering[r.id] && !lateIds.has(covering[r.id])))
  if (visible.length) {
    const kinds = [...new Set(visible.map((r) => SOURCE_KINDS[r.id] ?? r.provides.toLowerCase()))]
    parts.push(
      `${andList(visible.map((r) => shortName(r.name)))} ${visible.length === 1 ? 'is' : 'are'} running later than usual, so the newest hours of ${andList(kinds)} may be missing for now.`,
    )
  }
  if (!forecast.in_use) {
    parts.push(
      forecast.fallback === 'openmeteo'
        ? 'Our forecast is out of date, so forecasts for locations inside our area come from Open-Meteo until it updates. Maps show no forecast meanwhile.'
        : forecast.cycle
          ? 'Our forecast is out of date, so forecast days may be missing until it updates.'
          : 'We have no forecast right now.',
    )
  }
  if (parts.length) {
    const level = !forecast.in_use && visible.length ? 'down' : 'late'
    return { level, text: parts.join(' ') }
  }
  const observed = sent
    .map((r) => report.archive.last_hour_by_source[r.id])
    .filter(Boolean)
    .sort()
    .at(-1) as string
  const issued = forecast.cycle ? ` and the forecast issued ${cstTime(forecast.cycle)}` : ''
  return {
    level: 'ok',
    text: `All data are up to date, with weather observed through ${cstTime(observed)}${issued}.`,
  }
}

// The kinds of data `gaps` checks, by the variable each is checked by (ops.status.SOURCE_VARIABLES)
export const GAP_KINDS: Record<string, string> = {
  air_temperature: 'Temperature, humidity and wind',
  precipitation: 'Precipitation',
  shortwave_radiation: 'Solar radiation',
  soil_temperature_4cm: 'Soil temperature, soil moisture and snow depth',
}

const SHORT_DAY = new Intl.DateTimeFormat('en-US', { timeZone: 'UTC', month: 'short', day: 'numeric' })

/** "Nov 3" for an ISO date */
export function shortDay(iso: string): string {
  return SHORT_DAY.format(new Date(`${iso}T00:00:00Z`))
}

export type GapRow = { variable: string; kind: string; sources: string; days: { date: string; text: string }[] }

/** Each kind of data with its days missing hours: "Nov 3 (5 hours)" */
export function gapRows(report: StatusData, sources: StatusSource[]): GapRow[] {
  const names = new Map(sources.map((s) => [s.id, shortName(s.name)]))
  return report.gaps.variables.map((v) => ({
    variable: v.variable,
    kind: GAP_KINDS[v.variable] ?? v.variable,
    sources: andList(v.sources.map((s) => names.get(s) ?? s)),
    days: v.days.map((d) => ({
      date: d.date,
      text: `${shortDay(d.date)} (${d.missing_hours === 1 ? '1 hour' : `${d.missing_hours} hours`})`,
    })),
  }))
}

/** The gaps in a sentence: none at all, or how many days of which kinds */
export function gapsSummary(rows: GapRow[], first: string | null): string {
  const since = first ? ` since ${shortDay(first)}` : ''
  const withGaps = rows.filter((r) => r.days.length)
  if (!rows.length) return 'We haven’t checked the archive for gaps yet.'
  if (!withGaps.length) return `No hours are missing from the archive${since}.`
  return `Some hours are missing from the archive${since}: ${andList(
    withGaps.map((r) => `${r.kind.toLowerCase()} on ${r.days.length === 1 ? '1 day' : `${r.days.length} days`}`),
  )}.`
}
