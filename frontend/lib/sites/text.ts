// The site page's words and choices that don't need a component: where a location is, whose days it uses, what
// a risk level looks like, and the requests the Weather tab makes for a range.

import type { LocateData, TableResponse } from '@/types/api'

import { addDays } from '../dates'

/** "Waushara County, WI", or the state alone, or null where neither is known (outside the US) */
export function placeName(location: Pick<LocateData, 'county' | 'state'> | null): string | null {
  if (!location) return null
  if (location.county && location.state) return `${location.county}, ${location.state}`
  return location.state ?? location.county ?? null
}

/** "44.12° N, 89.52° W" */
export function coordinates(lat: number, lng: number): string {
  const part = (value: number, positive: string, negative: string) =>
    `${Math.abs(Number(value.toFixed(4)))}° ${value >= 0 ? positive : negative}`
  return `${part(lat, 'N', 'S')}, ${part(lng, 'E', 'W')}`
}

/** Whose days the site's daily values use (D74): the grid's inside the area we cover, the location's own outside */
export function dayBasisWords(location: Pick<LocateData, 'in_box' | 'timezone'> | null): string {
  if (!location || location.in_box)
    return 'Days run midnight to midnight Central Standard Time all year, as on our maps.'
  const zone = location.timezone ? ` (${location.timezone.replace(/_/g, ' ')})` : ''
  return `Days run midnight to midnight on this location's own clock${zone}, with daylight saving time.`
}

/** Where the site's weather comes from */
export function sourceWords(location: Pick<LocateData, 'in_box'> | null): string {
  if (!location || location.in_box)
    return 'Inside the area we cover: weather from NOAA’s hourly analyses and forecasts on a 2.5 km (1.5 mile) grid.'
  return 'Outside the area we cover: its weather comes from Open-Meteo’s models rather than NOAA’s 2.5 km grid, and it isn’t on our maps.'
}

export type RiskRow = {
  model: string
  name: string
  group: string
  level: number | null
  label: string | null
  inSeason: boolean | null
  reason: string | null
  missingDays: number
}

/** `/risk`'s columns as one row per model, highest risk first, then by name */
export function riskRows(body: Pick<TableResponse, 'data'>): RiskRow[] {
  const data = body.data as Record<string, (string | number | boolean | null)[]>
  const models = (data.model ?? []) as string[]
  return models
    .map((model, i) => ({
      model,
      name: String(data.name?.[i] ?? model),
      group: String(data.group?.[i] ?? ''),
      level: (data.risk_level?.[i] as number | null) ?? null,
      label: (data.risk_label?.[i] as string | null) ?? null,
      inSeason: (data.in_season?.[i] as boolean | null) ?? null,
      reason: (data.reason?.[i] as string | null) ?? null,
      missingDays: Number(data.missing_days?.[i] ?? 0),
    }))
    .toSorted((a, b) => (b.level ?? -1) - (a.level ?? -1) || a.name.localeCompare(b.name))
}

export type Range = 'week' | 'month' | 'season' | 'custom'

/** The first and last day the Weather tab asks for: the past week or 30 days, or the season from January 1,
 * through the forecast (no `end`) unless a custom range names its last day */
export function rangeDays(
  range: Range,
  today: string,
  custom: { start: string; end: string } | null,
): { start: string; end: string | null } {
  if (range === 'custom' && custom) return custom
  if (range === 'season') return { start: `${today.slice(0, 4)}-01-01`, end: null }
  return { start: addDays(today, range === 'week' ? -7 : -30), end: null }
}
