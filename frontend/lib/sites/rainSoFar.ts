import type { TableResponse } from '@/types/api'

import { formatHour } from '../charts/kinds'
import type { Units } from '../units'

// Today's precipitation so far (Ben, 2026-11-26): the API leaves a day still in progress without a total, so a
// site's today adds up its hours instead, through the newest hour that has a value, and says so: the hours reach
// AgWeather some hours after the rain falls, and nobody should read the number as live. The day is the point's own
// (CLAUDE.md, Time): midnight to midnight CST inside the area we cover, midnight on its own clock outside. A window
// holds the readings stamped after its start through its end. Precipitation is never estimated (D45): an hour
// without a value counts as none and is reported as missing.

export type DayBasis = { in_box: boolean; timezone: string | null }

export type RainSoFar = {
  /** Millimeters from the day's start through `through` */
  amount: number
  /** The newest hour with a value (UTC, as the API stamps it) */
  through: string
  /** Hours from the day's start through `through` without a value */
  missing: number
  /** The clock to show `through` on */
  timeZone: string
}

const HOUR = 3_600_000
// The grid's days run midnight to midnight CST all year (D74)
const GRID_OFFSET_HOURS = -6

/** Minutes the zone's clock is ahead of UTC at an instant */
function zoneOffset(at: number, timeZone: string): number {
  const parts = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone,
      hourCycle: 'h23',
      year: 'numeric',
      month: 'numeric',
      day: 'numeric',
      hour: 'numeric',
      minute: 'numeric',
    })
      .formatToParts(new Date(at))
      .map((p) => [p.type, Number(p.value)]),
  )
  const local = Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute)
  return Math.round((local - at) / 60_000)
}

/** When the point's day `date` (YYYY-MM-DD) starts, as a UTC instant in milliseconds */
export function dayStart(date: string, basis: DayBasis): number {
  const midnight = Date.parse(`${date}T00:00:00Z`)
  if (basis.in_box || !basis.timezone) return midnight - GRID_OFFSET_HOURS * HOUR
  // Midnight on the zone's clock: guess with the offset at UTC midnight, then once more for a change of offset
  let start = midnight - zoneOffset(midnight, basis.timezone) * 60_000
  start = midnight - zoneOffset(start, basis.timezone) * 60_000
  return start
}

/** The hours of the day starting at `start` added up, through the newest with a value; null before any has one */
export function sumSoFar(
  hours: { time: string; value: number | null; forecast: boolean }[],
  start: number,
  timeZone: string,
): RainSoFar | null {
  const end = start + 24 * HOUR
  const today = hours.filter((h) => {
    const t = Date.parse(h.time)
    return !h.forecast && t > start && t <= end
  })
  const newest = today.findLast((h) => h.value !== null)
  if (!newest) return null
  const through = Date.parse(newest.time)
  const known = today.filter((h) => h.value !== null && Date.parse(h.time) <= through)
  return {
    amount: known.reduce((sum, h) => sum + (h.value ?? 0), 0),
    through: newest.time,
    missing: Math.round((through - start) / HOUR) - known.length,
    timeZone,
  }
}

/** Today so far at each point of a `/weather/hourly` answer (`precipitation` in mm; one point or `points=`) */
export function rainSoFarByPoint(body: TableResponse, count: number, today: string): (RainSoFar | null)[] {
  const data = body.data as Record<string, unknown[]>
  const meta = body.meta as { location?: DayBasis; locations?: DayBasis[] }
  const bases = meta.locations ?? (meta.location ? [meta.location] : [])
  const times = (data.time ?? []) as string[]
  return Array.from({ length: count }, (_, k) => {
    const basis = bases[k]
    if (!basis) return null
    const hours = times
      .map((time, i) => ({
        time,
        point: data.point ? Number(data.point[i]) : 0,
        value: typeof data.precipitation?.[i] === 'number' ? (data.precipitation[i] as number) : null,
        forecast: data.kind?.[i] === 'forecast',
      }))
      .filter((h) => h.point === k)
    return sumSoFar(hours, dayStart(today, basis), basis.timezone ?? 'America/Chicago')
  })
}

/** "0.12 in so far today, through Nov 25, 2 p.m. CST" (with "; 2 hours missing") */
export function rainSoFarText(r: RainSoFar, units: Units): string {
  return `${units.format('mm', r.amount)} so far today, through ${formatHour(r.through, r.timeZone)}${missingWords(r)}`
}

/** "; 2 hours missing", or nothing */
export function missingWords(r: RainSoFar): string {
  return r.missing ? `; ${r.missing} ${r.missing === 1 ? 'hour' : 'hours'} missing` : ''
}

/** The short form for a day's card: "0.12 in so far" */
export function rainSoFarShort(r: RainSoFar, units: Units): string {
  return `${units.format('mm', r.amount)} so far`
}

/** What the number is not: the reader's warning beside it (followed by a link to the radar) */
export const NOT_LIVE = 'This is not live: precipitation reaches AgWeather some hours after it falls.'

/** The map at a point with the radar overlay on */
export function radarUrl(mapPath: string, lat: number, lng: number): string {
  const query = new URLSearchParams({ overlay: 'radar', c: `${lat.toFixed(3)},${lng.toFixed(3)}`, z: '8' })
  return `${mapPath}?${query}`
}
