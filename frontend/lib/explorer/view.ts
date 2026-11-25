// The map explorer's view (Phase 7 track 2, D118): every setting a reader can change, as typed state that the
// Share link carries (`lib/viewState.ts`), and the one pure function that turns it into the tiles' request, so the
// map, the cell panel's series and a shared link all read the view the same way.

import { addDays, parseDate } from '@/lib/dates'
import { OVERLAY_ORDER, type OverlayId } from '@/lib/map/overlays'
import { codecs, field, type Fields, type LatLng } from '@/lib/viewState'
import type { LayerInfo } from '@/types/api'

export const SPANS = ['day', 'hour', 'range', 'season'] as const
export type Span = (typeof SPANS)[number]

export const STATS = ['sum', 'mean', 'min', 'max'] as const
export type Stat = (typeof STATS)[number]

export const PLANTINGS = ['early', 'mid', 'late', 'none'] as const
export type Planting = (typeof PLANTINGS)[number]

export const ROLLS = [7, 14, 28] as const

export type ExplorerView = {
  /** A `/layers` id; null until the first visit's default is chosen */
  layer: string | null
  /** A model layer's output (`output=`); null: the layer's default (its first) */
  output: string | null
  /** The crop the Crops and pests picker shows */
  crop: string | null
  span: Span
  /** The day shown, or a range's or season's last day; null: the latest (a link without a date stays current) */
  date: string | null
  /** An hourly layer's hour in UTC, `2026-11-25T15`; null: the latest */
  hour: string | null
  /** A range's first day */
  start: string | null
  stat: Stat | null
  /** A window of days ending on (or centered on) the date: 7, 14 or 28 */
  roll: number | null
  align: 'trailing' | 'centered'
  /** Degree days' setting, written in °F: `modified_50_86` */
  dd: string | null
  /** Degree days counted from a day: a month and day (`04-15`) or a date; null: January 1 */
  biofix: string | null
  planting: Planting | null
  /** A model's options, `name:value` */
  opts: string[]
  /** A `/palettes` id (`_r` reversed); null: the layer's own */
  palette: string | null
  /** `default` (the layer's fixed range) or `low,high` in the reader's units; null: this map's own range */
  scale: string | null
  /** The cell clicked */
  at: LatLng | null
  /** The map's center and zoom, carried by a shared link */
  c: LatLng | null
  z: number | null
  /** The data overlay a shared link shows (radar, rain, the Drought Monitor); the basemap stays the reader's own.
   * Written only by Share: the map keeps its overlay in this browser's map settings */
  overlay: OverlayId | null
}

const option = {
  parse: (text: string) => (/^[a-z0-9_]+:[^,]+$/i.test(text) ? text : undefined),
  format: (value: string) => value,
}

export const VIEW_FIELDS: Fields<ExplorerView> = {
  layer: field(codecs.string, null),
  output: field(codecs.string, null),
  crop: field(codecs.string, null),
  span: field(codecs.oneOf(SPANS), 'day'),
  date: field(codecs.date, null),
  hour: field(
    { parse: (t: string) => (/^\d{4}-\d{2}-\d{2}T\d{2}$/.test(t) ? t : undefined), format: (t: string) => t },
    null,
  ),
  start: field(codecs.date, null),
  stat: field(codecs.oneOf(STATS), null),
  roll: field(codecs.integer({ min: 2, max: 365 }), null),
  align: field(codecs.oneOf(['trailing', 'centered'] as const), 'trailing'),
  dd: field(
    {
      parse: (t: string) => (/^(sine|modified|average)_[\dp.]+(_[\dp.]+)?$/.test(t) ? t : undefined),
      format: (t: string) => t,
    },
    null,
  ),
  biofix: field(
    { parse: (t: string) => (/^(\d{4}-)?\d{2}-\d{2}$/.test(t) ? t : undefined), format: (t: string) => t },
    null,
  ),
  planting: field(codecs.oneOf(PLANTINGS), null),
  opts: field(codecs.list(option), []),
  palette: field(codecs.string, null),
  scale: field(codecs.string, null),
  at: field(codecs.latLng(4), null),
  c: field(codecs.latLng(3), null),
  z: field(codecs.number({ digits: 2, min: 0, max: 22 }), null),
  overlay: field(codecs.oneOf(OVERLAY_ORDER), null),
}

/** The degree-day setting a first visit and the Degree days tab start from */
export const DEFAULT_DD = 'modified_50_86'

/** The first visit's layer (Ben, 2026-11-26): degree days (modified 50/86 °F) since January 1 from April to
 * October, the daily minimum temperature from November to March */
export function firstView(today: string): Partial<ExplorerView> {
  const month = Number(today.slice(5, 7))
  if (month >= 4 && month <= 10) return { layer: 'degree_days', dd: DEFAULT_DD, span: 'season' }
  return { layer: 'air_temperature_min', span: 'day' }
}

/** What a layer's time controls offer */
export function spansFor(layer: Pick<LayerInfo, 'group' | 'time_axis' | 'stats'>): Span[] {
  if (layer.time_axis === 'hour') return ['hour']
  if (layer.time_axis !== 'day') return []
  if (layer.group === 'running_total') return ['day']
  if (layer.group === 'degree_days') return ['day', 'range', 'season']
  const spans: Span[] = ['day']
  if (layer.stats.length) spans.push('range')
  if (layer.group === 'weather' && layer.stats.includes('sum')) spans.push('season')
  return spans
}

/** The span a layer shows for the view's: the view's if the layer has it, else its first */
export function spanFor(view: Pick<ExplorerView, 'span'>, layer: Parameters<typeof spansFor>[0]): Span | null {
  const spans = spansFor(layer)
  return spans.includes(view.span) ? view.span : (spans[0] ?? null)
}

/** The latest day (or hour) a layer has: the last observed */
export const latestOf = (layer: Pick<LayerInfo, 'range'>): string | null => layer.range.last

/** The day the view shows, or ends on: its date, else the layer's latest */
export function dayOf(view: Pick<ExplorerView, 'date'>, layer: Pick<LayerInfo, 'range'>): string | null {
  return view.date ?? latestOf(layer)?.slice(0, 10) ?? null
}

/** A biofix as a date on or before `end`: `04-15` is the latest April 15 on or before it */
export function biofixDate(biofix: string, end: string): string {
  if (biofix.length === 10) return biofix
  const sameYear = `${end.slice(0, 4)}-${biofix}`
  return sameYear <= end ? sameYear : `${Number(end.slice(0, 4)) - 1}-${biofix}`
}

/** A season to date's first day: the biofix for degree days, else January 1 of the end's year */
export function seasonStart(view: Pick<ExplorerView, 'biofix'>, layer: Pick<LayerInfo, 'group'>, end: string): string {
  if (layer.group === 'degree_days' && view.biofix) return biofixDate(view.biofix, end)
  return `${end.slice(0, 4)}-01-01`
}

/** A range's first day: the view's, else 14 days before its end; never after the end */
export function rangeStart(view: Pick<ExplorerView, 'start'>, end: string): string {
  const start = view.start ?? addDays(end, -13)
  return start > end ? end : start
}

export type TileRequest = {
  layer: string
  /** `{time}`: a day, an hour, `start..end` with a stat, or `latest` */
  time: string
  stat: Stat | null
  /** Everything else the tiles take, as query parameters (left out when null) */
  params: Record<string, string | number | null>
}

/** The statistic a range of a layer takes: the view's if the layer has it, else a sum where values add, else a mean */
export function statFor(view: Pick<ExplorerView, 'stat'>, layer: Pick<LayerInfo, 'stats' | 'group'>): Stat {
  const stats = layer.group === 'degree_days' ? ['sum', 'mean', 'min', 'max'] : layer.stats
  if (view.stat && stats.includes(view.stat)) return view.stat
  return stats.includes('sum') ? 'sum' : 'mean'
}

/** Whether a layer can be smoothed by a window of days (daily weather, degree days by the day) */
export const rollable = (layer: Pick<LayerInfo, 'group' | 'time_axis'>, span: Span | null): boolean =>
  span === 'day' && layer.time_axis === 'day' && (layer.group === 'weather' || layer.group === 'degree_days')

/**
 * The tiles' request for a view of a layer: `{time}` and the settings, as `/tiles/{layer}/{time}/…` takes them.
 * Degree days and model options are always written in US units (`units=us`), so a reader's metric setting
 * changes only what's shown. `null` when the layer can't be shown on its own (no time to show yet).
 */
export function tileRequest(view: ExplorerView, layer: LayerInfo): TileRequest | null {
  const span = spanFor(view, layer)
  const params: TileRequest['params'] = { units: 'us' }
  let time = 'latest'
  let stat: Stat | null = null

  if (layer.group === 'degree_days') params.dd = view.dd ?? DEFAULT_DD
  if (layer.group === 'model') {
    params.output = view.output && layer.outputs?.some((o) => o.name === view.output) ? view.output : null
    if (layer.planting?.length && view.planting && layer.planting.includes(view.planting))
      params.planting = view.planting
    for (const pair of view.opts) {
      const [name, value] = pair.split(':')
      if (layer.options?.includes(name)) params[name] = value
    }
  }

  if (span === 'hour') {
    time = view.hour ?? 'latest'
  } else if (span === 'day') {
    time = view.date ?? 'latest'
    if (view.roll && rollable(layer, span)) {
      params.roll = view.roll
      params.roll_align = view.align === 'centered' ? 'centered' : null
      // A window needs one day to end on; a sum where values add, else a mean (the API's default)
    }
  } else if (span === 'range' || span === 'season') {
    const end = dayOf(view, layer)
    if (!end) return null
    const start = span === 'season' ? seasonStart(view, layer, end) : rangeStart(view, end)
    time = `${start}..${end}`
    stat =
      span === 'season'
        ? layer.stats.includes('sum') || layer.group === 'degree_days'
          ? 'sum'
          : 'mean'
        : statFor(view, layer)
  }
  return { layer: layer.id, time, stat, params }
}

/** The days a stepper may reach for a daily layer: the archive's first to the forecast's last */
export function dayBounds(layer: Pick<LayerInfo, 'range'>): { first: string | null; last: string | null } {
  const { first, last, forecast_through } = layer.range
  return { first: first?.slice(0, 10) ?? null, last: (forecast_through ?? last)?.slice(0, 10) ?? null }
}

/** A day moved by `days`, held within the layer's bounds */
export function stepDay(day: string, days: number, layer: Pick<LayerInfo, 'range'>): string {
  const { first, last } = dayBounds(layer)
  let next = addDays(day, days)
  if (first && next < first) next = first
  if (last && next > last) next = last
  return next
}

/** An hour (`2026-11-25T15`, UTC) moved by `hours`, held within the layer's bounds */
export function stepHour(hour: string, hours: number, layer: Pick<LayerInfo, 'range'>): string {
  const at = new Date(`${hour}:00:00Z`)
  at.setUTCHours(at.getUTCHours() + hours)
  let next = at.toISOString().slice(0, 13)
  const first = layer.range.first?.slice(0, 13)
  const last = (layer.range.forecast_through ?? layer.range.last)?.slice(0, 13)
  if (first && next < first) next = first
  if (last && next > last) next = last
  return next
}

/** The day (or an hourly layer's hour) the time stepper moves: the view's, else the layer's latest */
export function stepperWhen(view: ExplorerView, layer: LayerInfo, today: string): string | null {
  const span = spanFor(view, layer)
  if (span === 'hour') return view.hour ?? layer.range.last?.slice(0, 13) ?? null
  if (span === null) return null
  return dayOf(view, layer) ?? today
}

/** The view's change for a step to `when`: a range keeps its length, moving its first day with its last */
export function stepTo(view: ExplorerView, layer: LayerInfo, when: string): Partial<ExplorerView> {
  const span = spanFor(view, layer)
  if (span === 'hour') return { hour: when }
  if (span === 'range') {
    const end = dayOf(view, layer)
    if (end) {
      const length = Math.round((Date.parse(end) - Date.parse(rangeStart(view, end))) / 86_400_000)
      return { date: when, start: addDays(when, -length) }
    }
  }
  return { date: when }
}

/** Whether a day (or hour) is past the last observed one: a forecast */
export function isForecast(when: string, layer: Pick<LayerInfo, 'range'>): boolean {
  const last = layer.range.last
  if (!last) return false
  return when.length > 10 ? when.slice(0, 13) > last.slice(0, 13) : when > last.slice(0, 10)
}

/** Whether a map's `{time}` (a day, an hour, `start..end`, or `latest`) ends in the forecast */
export function timeIsForecast(time: string, layer: Pick<LayerInfo, 'range'>): boolean {
  if (time === 'latest') return false
  return isForecast(time.split('..').at(-1)!, layer)
}

/** The month (1–12) of an ISO date */
export const monthOf = (iso: string) => parseDate(iso).getUTCMonth() + 1
