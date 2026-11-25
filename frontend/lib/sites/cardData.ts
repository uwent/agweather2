// What a site's card on /sites asks the API and how it reads the answers: `/risk` for today with the site's
// models (its preferences), and `/weather/daily` for today and tomorrow, several sites in one request.

import { addDays } from '@/lib/dates'
import { riskRank } from '@/lib/riskLevels'
import type { EffectivePrefs } from '@/lib/sites.svelte'
import type { ModelEntry } from '@/types'
import type { TableResponse } from '@/types/api'

/** Columns of a table answer (the default orientation) */
export type Columns = Record<string, (number | string | boolean | null)[]>

export function columns(body: TableResponse): Columns {
  return Array.isArray(body.data) ? {} : body.data
}

/** The models a card asks `/risk` for: the site's chosen models; else every model with risk for its chosen crops;
 * else none named, so the API answers with those in season and in their region. Hidden ones are left out (and, when
 * the API picks, filtered from its answer by `topRisks`). */
export function riskModels(prefs: EffectivePrefs, catalog: readonly ModelEntry[]): string[] | undefined {
  const withRisk = catalog.filter((m) => m.risk_levels.length > 0)
  let chosen: string[] | undefined
  if (prefs.models) chosen = prefs.models.filter((id) => withRisk.some((m) => m.id === id))
  else if (prefs.crops) chosen = withRisk.filter((m) => m.crops.some((c) => prefs.crops!.includes(c))).map((m) => m.id)
  return chosen?.filter((id) => !prefs.hiddenModels.includes(id))
}

export type RiskRow = {
  model: string
  name: string
  level: number
  label: string
  /** The number of levels in its scale, for the color */
  levels: number
}

export type RiskSummary = {
  /** The highest risks, most first (at most `top`) */
  top: RiskRow[]
  /** Models with a risk today beyond the top ones */
  more: number
  /** Models with no risk today (out of season, before a biofix, no data) */
  none: number
}

/** The card's risks from a `/risk` answer: the `top` highest by where they sit on their scale (ties by name), the rest
 * counted. Hidden models are dropped. */
export function topRisks(
  body: TableResponse,
  catalog: readonly ModelEntry[],
  hidden: readonly string[] = [],
  top = 3,
): RiskSummary {
  const c = columns(body)
  const ids = (c.model ?? []) as string[]
  const rows: RiskRow[] = []
  let none = 0
  ids.forEach((id, k) => {
    if (hidden.includes(id)) return
    const level = c.risk_level?.[k]
    const label = c.risk_label?.[k]
    if (typeof level !== 'number' || typeof label !== 'string') {
      none++
      return
    }
    const levels = catalog.find((m) => m.id === id)?.risk_levels.length ?? 5
    rows.push({ model: id, name: String(c.name?.[k] ?? id), level, label, levels })
  })
  rows.sort((a, b) => riskRank(b.level, b.levels) - riskRank(a.level, a.levels) || a.name.localeCompare(b.name))
  return { top: rows.slice(0, top), more: Math.max(0, rows.length - top), none }
}

/** Stored units of the weather columns a card asks for (`units=metric` returns them so; lib/units converts) */
export const WEATHER_UNITS = {
  air_temperature_max: 'degC',
  air_temperature_min: 'degC',
  precipitation_sum: 'mm',
} as const

export type DayWeather = {
  date: string
  kind: string | null
  high: number | null
  low: number | null
  precipitation: number | null
}

export type SiteWeather = { today: DayWeather | null; tomorrow: DayWeather | null }

/** The `/weather/daily` query for several sites' today and tomorrow */
export function weatherQuery(points: readonly { lat: number; lng: number }[], today: string) {
  return {
    points: points.map((p) => `${p.lat},${p.lng}`).join(';'),
    vars: Object.keys(WEATHER_UNITS),
    start: today,
    end: addDays(today, 1),
    units: 'metric',
  }
}

/** Each point's today and tomorrow from a `/weather/daily` answer (its `point` column indexes the request's points) */
export function weatherByPoint(body: TableResponse, count: number, today: string): SiteWeather[] {
  const c = columns(body)
  const out: SiteWeather[] = Array.from({ length: count }, () => ({ today: null, tomorrow: null }))
  const tomorrow = addDays(today, 1)
  const num = (v: unknown) => (typeof v === 'number' ? v : null)
  ;(c.point ?? []).forEach((point, k) => {
    const site = out[Number(point)]
    if (!site) return
    const day: DayWeather = {
      date: String(c.date?.[k]),
      kind: (c.kind?.[k] as string | null) ?? null,
      high: num(c.air_temperature_max?.[k]),
      low: num(c.air_temperature_min?.[k]),
      precipitation: num(c.precipitation_sum?.[k]),
    }
    if (day.date === today) site.today = day
    else if (day.date === tomorrow) site.tomorrow = day
  })
  return out
}
