// The date control's timeline (Phase 7 track 2; Ben, 2026-11-26): the days (or hours) its slider runs over, which of
// them can be chosen, and where the observed days end and the forecast begins. A daily layer's timeline is the
// chosen day's year, January to December, as the alfalfa tool's slider is its chosen year; an hourly layer's is the
// 7 days (midnight to midnight CST) around the newest hour, or around the chosen hour when that's further back.
// Positions are indexes into the window; on the track, index i fills [i, i + 1) / count.

import { addDays, daysBetween, formatDate, SHORT_MONTHS } from '@/lib/dates'
import type { LayerInfo } from '@/types/api'

import { dayBounds, stepDay } from './view'

export type Tick = {
  /** The tick's place on the track, 0–1 */
  at: number
  label: string
  /** Left unlabelled where the track is narrow */
  minor: boolean
}

export type Timeline = {
  unit: 'day' | 'hour'
  /** The window's first day (`2026-01-01`) or hour (`2026-11-22T06`, UTC) */
  start: string
  /** Days or hours in the window */
  count: number
  /** The first and last index that can be chosen */
  min: number
  max: number
  /** The last observed day's or hour's index: before the window (negative) or past it (≥ count) as it falls */
  observed: number
  ticks: Tick[]
}

type Ranged = Pick<LayerInfo, 'range'>

const clamp = (n: number, low: number, high: number) => Math.min(high, Math.max(low, n))

/** An hour (`2026-11-25T20`, UTC) moved by `hours` */
export function addHours(hour: string, hours: number): string {
  return new Date(Date.parse(`${hour.slice(0, 13)}:00:00Z`) + hours * 3600_000).toISOString().slice(0, 13)
}

const hoursBetween = (from: string, to: string) =>
  Math.round((Date.parse(`${to.slice(0, 13)}:00:00Z`) - Date.parse(`${from.slice(0, 13)}:00:00Z`)) / 3600_000)

/** The hour (UTC) the CST day holding `hour` begins: CST midnight is 06Z */
export function cstDayStart(hour: string): string {
  const cstDate = addHours(hour, -6).slice(0, 10)
  return `${cstDate}T06`
}

/** The day or hour at an index */
export const whenAt = (t: Timeline, index: number): string =>
  t.unit === 'day' ? addDays(t.start, index) : addHours(t.start, index)

/** A day's or hour's index (outside 0..count-1 when it's outside the window) */
export const indexOf = (t: Timeline, when: string): number =>
  t.unit === 'day' ? daysBetween(t.start, when.slice(0, 10)) : hoursBetween(t.start, when)

/** An index's left edge on the track, 0–1 */
export const edgeOf = (t: Timeline, index: number): number => index / t.count

/** An index's center on the track, where the slider's thumb sits */
export const centerOf = (t: Timeline, index: number): number => (index + 0.5) / t.count

/** The index under a place on the track (a pointer's), held to what can be chosen */
export const indexAt = (t: Timeline, at: number): number => clamp(Math.floor(at * t.count), t.min, t.max)

/** An index moved by `by`, held to what can be chosen */
export const moveBy = (t: Timeline, index: number, by: number): number => clamp(index + by, t.min, t.max)

/** Where the forecast begins on the track, or null when the window has no observed and forecast days side by side */
export function boundaryOf(t: Timeline): number | null {
  if (t.observed < t.min || t.observed >= t.max) return null
  return edgeOf(t, t.observed + 1)
}

/** The track's observed and forecast parts, each `[from, to]` on 0–1, null when the window has none */
export function segmentsOf(t: Timeline): { observed: [number, number] | null; forecast: [number, number] | null } {
  const lastObserved = Math.min(t.observed, t.max)
  const firstForecast = Math.max(t.observed + 1, t.min)
  return {
    observed: lastObserved >= t.min ? [edgeOf(t, t.min), edgeOf(t, lastObserved + 1)] : null,
    forecast: firstForecast <= t.max ? [edgeOf(t, firstForecast), edgeOf(t, t.max + 1)] : null,
  }
}

/** A range's band on the track, `[from, to]` on 0–1 and clipped to the window; null when it's outside */
export function bandOf(t: Timeline, from: string, to: string): [number, number] | null {
  const a = Math.max(0, indexOf(t, from))
  const b = Math.min(t.count, indexOf(t, to) + 1)
  return b > a ? [edgeOf(t, a), edgeOf(t, b)] : null
}

/** How the boundary's two labels ("Observed through …", "Forecast") sit around it: either side ('split'), both
 * ending at it when it's near the track's right end ('before'), both starting at it near the left ('after') */
export function labelPlacement(boundary: number): 'split' | 'before' | 'after' {
  if (boundary > 0.75) return 'before'
  if (boundary < 0.3) return 'after'
  return 'split'
}

/** A daily layer's timeline: the year holding `day`; null for a layer without days */
export function dayTimeline(layer: Ranged, day: string): Timeline | null {
  const { first, last } = dayBounds(layer)
  const observed = layer.range.last?.slice(0, 10)
  if (!first || !last || !observed) return null
  const year = Number(day.slice(0, 4))
  const start = `${year}-01-01`
  const count = daysBetween(start, `${year + 1}-01-01`)
  const t: Timeline = {
    unit: 'day',
    start,
    count,
    min: clamp(daysBetween(start, first), 0, count - 1),
    max: clamp(daysBetween(start, last), 0, count - 1),
    observed: daysBetween(start, observed),
    ticks: [],
  }
  t.ticks = SHORT_MONTHS.map((label, m) => ({
    at: edgeOf(t, daysBetween(start, `${year}-${String(m + 1).padStart(2, '0')}-01`)),
    label,
    minor: m % 2 === 1,
  }))
  return t
}

/** The observed days a daily layer's recent timeline shows before the forecast */
export const RECENT_DAYS = 42

/** A daily layer's recent timeline: the last 6 weeks observed and the forecast, so the forecast's days have room on
 * the track (on a year's they're a sliver); weeks marked back from the newest observed day */
export function recentTimeline(layer: Ranged): Timeline | null {
  const { first, last } = dayBounds(layer)
  const observed = layer.range.last?.slice(0, 10)
  if (!first || !last || !observed) return null
  const start = addDays(observed, -(RECENT_DAYS - 1))
  const count = daysBetween(start, last) + 1
  const t: Timeline = {
    unit: 'day',
    start,
    count,
    min: clamp(daysBetween(start, first), 0, count - 1),
    max: count - 1,
    observed: RECENT_DAYS - 1,
    ticks: [],
  }
  const weeks = Math.ceil(count / 7)
  t.ticks = Array.from({ length: weeks }, (_, w) => ({
    at: edgeOf(t, w * 7),
    label: formatDate(addDays(start, w * 7)),
    minor: w % 2 === 1,
  }))
  return t
}

/** Whether a day is on a layer's recent timeline */
export function isRecent(day: string, layer: Ranged): boolean {
  const t = recentTimeline(layer)
  if (!t) return false
  const i = indexOf(t, day)
  return i >= t.min && i <= t.max
}

/** The days either side of the newest (or chosen) hour an hourly layer's timeline shows */
const HOUR_DAYS_BEFORE = 3
const HOUR_DAYS = 7

/** An hourly layer's timeline: the 7 CST days around the newest hour, or around `hour` when it's outside them */
export function hourTimeline(layer: Ranged, hour: string | null): Timeline | null {
  const { first, last: observed, forecast_through } = layer.range
  if (!first || !observed) return null
  const last = (forecast_through ?? observed).slice(0, 13)
  const around = (anchor: string) => addHours(cstDayStart(anchor), -24 * HOUR_DAYS_BEFORE)
  let start = around(observed)
  const count = 24 * HOUR_DAYS
  if (hour) {
    const at = hoursBetween(start, hour)
    if (at < 0 || at >= count) start = around(hour)
  }
  const t: Timeline = {
    unit: 'hour',
    start,
    count,
    min: clamp(hoursBetween(start, first), 0, count - 1),
    max: clamp(hoursBetween(start, last), 0, count - 1),
    observed: hoursBetween(start, observed),
    ticks: [],
  }
  t.ticks = Array.from({ length: HOUR_DAYS }, (_, d) => ({
    at: edgeOf(t, d * 24),
    // The CST date the day's midnight begins
    label: formatDate(addHours(start, d * 24 - 6)),
    minor: d % 2 === 1,
  }))
  return t
}

/** A no-year layer's timeline (the chance of a freeze on a day of the year): January to December of `day`'s year,
 * every day can be chosen, none of them observed or forecast */
export function noYearTimeline(day: string): Timeline {
  const year = Number(day.slice(0, 4))
  const start = `${year}-01-01`
  const count = daysBetween(start, `${year + 1}-01-01`)
  const t: Timeline = { unit: 'day', start, count, min: 0, max: count - 1, observed: count - 1, ticks: [] }
  t.ticks = SHORT_MONTHS.map((label, m) => ({
    at: edgeOf(t, daysBetween(start, `${year}-${String(m + 1).padStart(2, '0')}-01`)),
    label,
    minor: m % 2 === 1,
  }))
  return t
}

/** A no-year day moved by `days`, wrapping around within its year (December 31 + 1 is January 1) */
export function stepNoYear(day: string, days: number): string {
  const year = day.slice(0, 4)
  const count = daysBetween(`${year}-01-01`, `${Number(year) + 1}-01-01`)
  const index = (((daysBetween(`${year}-01-01`, day) + days) % count) + count) % count
  return addDays(`${year}-01-01`, index)
}

/** The years a daily layer has, newest first */
export function yearsOf(layer: Ranged): number[] {
  const { first, last } = dayBounds(layer)
  if (!first || !last) return []
  const years: number[] = []
  for (let y = Number(last.slice(0, 4)); y >= Number(first.slice(0, 4)); y--) years.push(y)
  return years
}

/** The same day of the year in another year (February 29 as the 28th), held to the layer's days */
export function inYear(day: string, year: number, layer: Ranged): string {
  let next = `${year}${day.slice(4, 10)}`
  if (next.endsWith('-02-29') && addDays(next.replace(/29$/, '28'), 1).endsWith('-03-01')) next = `${year}-02-28`
  return stepDay(next, 0, layer)
}
