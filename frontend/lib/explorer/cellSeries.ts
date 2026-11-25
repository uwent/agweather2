// The clicked cell's series (Phase 7 track 2 step 6): the request for the days around the map's date at one
// point, with the map's own settings (degree days, smoothing, the planting tier, a model's options), and the
// answer read into one series for the cell panel's chart. Maps default to `planting=mid` where a point defaults to
// no planting, so the tier is always sent: the panel's numbers then match the map's.

import { addDays } from '@/lib/dates'
import type { LatLng } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

import {
  dayOf,
  DEFAULT_DD,
  type ExplorerView,
  rangeStart,
  rollable,
  seasonStart,
  spanFor,
  type TileRequest,
} from './view'

/** Days shown before the map's day */
export const DAYS_BEFORE = 13
/** Hours shown around an hourly map's hour */
export const HOURS_BEFORE = 36
export const HOURS_AFTER = 12

/** Running totals charted by their daily values (the map is the total since January 1) */
const DAILY_OF_TOTAL: Record<string, string> = {
  precipitation_total: 'precipitation_sum',
  et0_total: 'et0_sum',
  water_balance_total: 'water_balance',
}

export type SeriesRequest = {
  path: string
  params: Record<string, string | number | null>
  /** The column the chart shows */
  column: string
  /** The first and last day (or hour) the chart shows; the answer may hold more (a model's season) */
  from: string
  to: string | null
  /** The chart shows each day of a running total, not the total */
  daily?: boolean
}

/**
 * The series behind the map's value at a point, or null for a layer with none yet (chill portions, climate).
 * `tiles` is the map's own request (`tileRequest`), whose settings this repeats.
 */
export function seriesRequest(
  view: ExplorerView,
  layer: LayerInfo,
  tiles: TileRequest,
  at: LatLng,
): SeriesRequest | null {
  const point = { lat: Number(at.lat.toFixed(4)), lng: Number(at.lng.toFixed(4)), units: 'us' }
  const span = spanFor(view, layer)

  if (layer.time_axis === 'hour') {
    const hour = view.hour ?? layer.range.last?.slice(0, 13)
    if (!hour) return null
    const shift = (hours: number) => {
      const at = new Date(`${hour}:00:00Z`)
      at.setUTCHours(at.getUTCHours() + hours)
      return at.toISOString().slice(0, 13)
    }
    const column = layer.variable ?? layer.id
    return {
      path: '/weather/hourly',
      params: { ...point, vars: column, start: shift(-HOURS_BEFORE), end: shift(HOURS_AFTER) },
      column,
      from: `${shift(-HOURS_BEFORE)}:00Z`,
      to: `${shift(HOURS_AFTER)}:00Z`,
    }
  }

  const day = dayOf(view, layer)
  if (!day) return null
  const from =
    span === 'season'
      ? seasonStart(view, layer, day)
      : span === 'range'
        ? rangeStart(view, day)
        : addDays(day, -DAYS_BEFORE)
  // Past days end on the map's day; the latest runs on through the forecast
  const last = layer.range.last?.slice(0, 10)
  const end = last && day < last ? day : null

  if (layer.group === 'model') {
    const params: SeriesRequest['params'] = { ...point, end }
    // The map's tier (mid by default); `none` is no planting date at all, as at a point by default
    if (layer.planting?.length) {
      const tier = typeof tiles.params.planting === 'string' ? tiles.params.planting : 'mid'
      if (tier !== 'none') params.planting_date = tier
    }
    for (const [name, value] of Object.entries(tiles.params)) {
      if (layer.options?.includes(name)) params[name] = value
    }
    const output =
      typeof tiles.params.output === 'string' ? tiles.params.output : (layer.outputs?.[0]?.name ?? 'risk_level')
    return { path: `/models/${encodeURIComponent(layer.id)}/run`, params, column: output, from, to: end }
  }

  if (layer.group === 'degree_days') {
    const dd = typeof tiles.params.dd === 'string' ? tiles.params.dd : DEFAULT_DD
    const cumulative = span === 'season'
    return {
      path: '/degree-days',
      params: { ...point, dd, start: from, end },
      column: cumulative ? `dd_${dd}_cum` : `dd_${dd}`,
      from,
      to: end,
    }
  }

  if (layer.group === 'running_total') {
    const daily = DAILY_OF_TOTAL[layer.id]
    if (!daily) return null
    return {
      path: '/weather/daily',
      params: { ...point, vars: daily, start: from, end },
      column: daily,
      from,
      to: end,
      daily: true,
    }
  }

  if (layer.group !== 'weather') return null
  const variable = layer.variable ?? layer.id
  const params: SeriesRequest['params'] = { ...point, vars: variable, start: from, end }
  let column = variable
  if (typeof tiles.params.roll === 'number' && rollable(layer, span)) {
    params.roll = tiles.params.roll
    params.roll_align = tiles.params.roll_align ?? null
    column = `${variable}_${tiles.params.roll}d`
  }
  return { path: '/weather/daily', params, column, from, to: end }
}

/** One series as the panel charts it */
export type CellSeries = {
  /** Days (`2026-07-08`) or hours (`2026-07-08T15:00Z`) */
  times: string[]
  values: (number | null)[]
  /** observed, partial, forecast or missing, per time */
  kinds: string[]
  /** The values' unit as the API labelled it (°F, in, °F·d), or '' */
  unit: string
  /** A risk level's names, for a model's levels */
  labels: (string | null)[] | null
  warnings: string[]
}

type Table = {
  meta: { units?: Record<string, string>; warnings?: string[] }
  data: Record<string, unknown[]>
}

/** The answer read into the chart's series, cut to the request's days */
export function readSeries(request: SeriesRequest, body: Table): CellSeries {
  const data = body.data
  const times = ((data.date ?? data.time ?? []) as string[]).map(String)
  const keep = times.map((time) => time >= request.from && (request.to === null || time.slice(0, 10) <= request.to))
  const pick = <T>(list: T[] | undefined) => (list ?? []).filter((_, i) => keep[i])
  const values = pick(data[request.column] as (number | null)[] | undefined).map((v) =>
    typeof v === 'number' && Number.isFinite(v) ? v : null,
  )
  const labels = request.column === 'risk_level' && data.risk_label ? pick(data.risk_label as (string | null)[]) : null
  return {
    times: pick(times),
    values,
    kinds: pick(data.kind as string[] | undefined).map(String),
    unit: body.meta.units?.[request.column] ?? '',
    labels,
    warnings: body.meta.warnings ?? [],
  }
}
