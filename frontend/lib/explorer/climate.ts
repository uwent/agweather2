// Climate on the map explorer (Phase 7 track 6 step 6.3, D86, D88): what "Compare with normal" offers a map, the
// days a range can count where their normals are kept, and a climate map's value at a cell in words. The rules
// mirror the API's (`api/climatemaps.py`), so the controls offer only maps it can draw:
//
// - a normal or departure for a layer that lists it, of one day (smoothed or not), a range's mean or total, a
//   running total on a day, degree days whose setting has kept running totals, or a stored count of days;
// - a percentile only for running totals from January 1 of precipitation and of modified 50/86 and single sine
//   41/86 degree days, over the 30 or 10 years;
// - the freeze maps at 32, 28 and 24 °F, over any of the periods.

import { NORMAL_PERIODS, type Period } from '@/lib/climate/periods'
import { chanceWords, ordinal, percentileWords, shareOfYears, thresholdLabel, thresholdNoun } from '@/lib/climate/words'
import { formatDate } from '@/lib/dates'
import { formatDays } from '@/lib/map/dataTiles'
import type { Units } from '@/lib/units'
import type { LayerCount, LayerInfo } from '@/types/api'

import { ddParts } from './catalog'

export const CLIMATE_KINDS = ['normal', 'departure', 'percentile'] as const
export type ClimateKind = (typeof CLIMATE_KINDS)[number]

/** The periods a climate map can come from (30 years by default, Ben 2026-11-26) */
export const MAP_PERIODS: readonly Period[] = NORMAL_PERIODS
export type MapPeriod = 'last30' | 'last10' | 'last5'

/** The freeze maps' thresholds, °F: frost, hard freeze, killing freeze (`normals.FREEZE_F`) */
export const FREEZE_MAP_F = [32, 28, 24] as const

/** The degree-day settings with percentile maps (`agdata.layers.NORMAL_DECILES`) */
export const PERCENTILE_DD = ['modified_50_86', 'sine_41_86']

/** The counts of days whose normals are kept (`agdata.normals.COUNTS`, D88), as `/layers` lists them on a layer:
 * `count=`'s value in US units, each with its bounds and the name a grower knows it by (or none) */
export const countsFor = (layer: Pick<LayerInfo, 'counts'>): string[] => (layer.counts ?? []).map((c) => c.count)

/** "Days at or above 93 °F (heat days)", in the reader's units */
export function countLabel(count: LayerCount, units: Units): string {
  const above = count.low !== null
  const bound = count.low ?? count.high
  if (bound === null) return count.count
  const unit = count.unit
  const digits = unit === 'degF' && units.system === 'metric' ? 1 : unit === 'MJ_m2' ? 0 : undefined
  const value = units.format(unit, bound, digits === undefined ? undefined : { digits })
  return `Days at or ${above ? 'above' : 'below'} ${value}${count.name ? ` (${count.name})` : ''}`
}

/** The degree-day settings with kept running totals: the `dd_*` running totals that list normals */
export function storedDd(layers: readonly Pick<LayerInfo, 'id' | 'group' | 'climate'>[]): string[] {
  return layers
    .filter((l) => l.group === 'running_total' && l.id.startsWith('dd_') && l.climate?.length)
    .map((l) => l.id.slice(3))
}

/** Whether a degree-day setting's normals are kept: a kept running total, or a single sine pair of two kept ones
 * (its normal is their difference) */
export function ddHasNormals(dd: string, stored: readonly string[]): boolean {
  if (stored.includes(dd)) return true
  const parts = ddParts(dd)
  if (!parts || parts.method !== 'sine' || parts.upper === null) return false
  const name = (v: number) => `sine_${String(v).replace('.', 'p')}`
  return stored.includes(name(parts.base)) && stored.includes(name(parts.upper))
}

/** What a map's comparison depends on */
export type ClimateCase = {
  layer: Pick<LayerInfo, 'id' | 'group' | 'climate' | 'time_axis' | 'counts'>
  /** The span the map shows (`spanFor`) */
  span: string | null
  /** Degree days' setting */
  dd: string | null
  biofix: string | null
  /** A count of days chosen on a range */
  count: string | null
  period: MapPeriod
  /** The degree-day settings with kept running totals; left out, any setting is taken */
  stored?: readonly string[]
}

/** The comparisons a map can show, in the order offered */
export function climateKinds(c: ClimateCase): ClimateKind[] {
  const listed = (c.layer.climate ?? []).filter((k): k is ClimateKind =>
    (CLIMATE_KINDS as readonly string[]).includes(k),
  )
  if (!listed.length || c.layer.time_axis !== 'day' || c.span === 'hour' || c.span === null) return []
  if (c.layer.group === 'degree_days' && c.dd && c.stored && !ddHasNormals(c.dd, c.stored)) return []
  if (c.count && !countsFor(c.layer).includes(c.count)) return []
  return listed.filter((kind) => kind !== 'percentile' || percentileFits(c))
}

/** A percentile ranks a running total from January 1, over the 30 or 10 years */
function percentileFits(c: ClimateCase): boolean {
  if (c.period === 'last5' || c.count) return false
  if (c.layer.group === 'running_total') return true
  if (c.layer.group === 'degree_days')
    return c.span === 'season' && (!c.biofix || c.biofix === '01-01') && PERCENTILE_DD.includes(c.dd ?? '')
  return false
}

/** A no-year day (`freeze_chance`'s) as the reader sees it: "May 1" */
export const monthDayText = (day: string): string => formatDate(`2024${day.slice(4, 10)}`)

/** The value at a cell of a climate map in words, or null for a map without climate. `value` is the tiles' (the
 * stored unit), `unit` the tiles' stored unit, `params` and `time` the tiles' own request (`tileRequest`). */
export function climateValueWords(args: {
  layer: Pick<LayerInfo, 'id' | 'group'>
  time: string
  params: Record<string, string | number | null>
  value: number | 'none' | null
  unit: string
  units: Units
  /** The years the map's normal comes from, in words: "1996–2025" */
  years?: string | null
}): string | null {
  const { layer, params, value, unit, units } = args
  if (value === null || value === 'none') return null
  const threshold = typeof params.threshold === 'number' ? params.threshold : 32
  const years = args.years ? ` (${args.years})` : ''

  if (layer.id === 'freeze_chance') {
    const day = args.time === 'latest' ? null : args.time
    const noun = thresholdNoun(threshold, units)
    const label = thresholdLabel(threshold, units)
    if (!day) return `A ${noun} in ${chanceWords(value)}${years}.`
    const spring = Number(day.slice(5, 7)) <= 6
    const when = monthDayText(day)
    return spring
      ? `${label} came after ${when} in ${chanceWords(value)}${years}.`
      : `${label} came on or before ${when} in ${chanceWords(value)}${years}.`
  }

  if (layer.id === 'freeze_dates') {
    const output = typeof params.output === 'string' ? params.output : 'last_spring_p10'
    const label = thresholdLabel(threshold, units)
    if (output === 'season_days_p50')
      return `${label}: the frost-free season lasts ${Math.round(value)} days in a typical year${years}.`
    const match = /^(last_spring|first_fall)_p(\d+)$/.exec(output)
    if (!match) return null
    const which = match[1] === 'last_spring' ? 'The last spring' : 'The first fall'
    return `${which} ${label.replace(/^./, (c) => c.toLowerCase())} came by ${formatDays(value, false)} in ${shareOfYears(Number(match[2]))}${years}.`
  }

  const kind = params.climate
  if (kind === 'percentile') {
    return `The ${ordinal(value)} percentile, ${percentileWords(value)}${years}.`
  }
  if (kind === 'departure') {
    const counted = typeof params.count === 'string'
    if (counted) {
      const days = Math.round(value * 10) / 10
      if (Math.abs(days) < 0.5) return `About as many days as normal${years}.`
      const n = Math.abs(days)
      return `${n.toLocaleString('en-US')} day${n === 1 ? '' : 's'} ${days > 0 ? 'more' : 'fewer'} than normal${years}.`
    }
    const shown = units.toDisplay(unit, value) ?? value
    // A temperature's difference to a tenth of a degree (a whole °F hides most of a day's departure)
    const digits = unit.startsWith('delta_') ? 1 : units.digits(unit)
    if (Number(Math.abs(shown).toFixed(digits)) === 0) return `Normal${years}.`
    const size = units.format(unit, Math.abs(value), { digits })
    return `${size} ${value > 0 ? 'above' : 'below'} normal${years}.`
  }
  if (kind === 'normal') return args.years ? `The average over ${args.years}.` : 'The normal.'
  return null
}

/** The comparisons in the reader's words, for the control */
export const KIND_LABELS: Record<ClimateKind | 'off', string> = {
  off: 'Off',
  normal: 'Normal',
  departure: 'Departure',
  percentile: 'Percentile',
}
