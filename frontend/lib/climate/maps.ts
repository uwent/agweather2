// The climate explorer's maps (`/climate`, Phase 7 track 6 step 6.4 as Ben changed it, 2026-11-26): a short list of
// climate maps, each a view of the map explorer (`lib/explorer/view.ts`), so the tiles come from the explorer's own
// `tileRequest` and "Open in the map explorer" opens the same map. Ranges end on the layer's latest observed day.

import { addDays } from '@/lib/dates'
import type { MapPeriod } from '@/lib/explorer/climate'
import { DEFAULT_DD, type ExplorerView, VIEW_FIELDS } from '@/lib/explorer/view'
import { routes } from '@/lib/routes'
import { defaults, toQuery, type LatLng } from '@/lib/viewState'
import type { Units } from '@/lib/units'
import type { LayerInfo } from '@/types/api'

import type { Period } from './periods'
import { temperatureText } from './words'

export const CLIMATE_MAPS = [
  'degree-days',
  'rain',
  'highs',
  'freeze-chance',
  'last-freeze',
  'first-freeze',
  'hot-days',
] as const
export type ClimateMap = (typeof CLIMATE_MAPS)[number]

export type ClimateMapText = {
  /** The map in the list */
  label: string
  /** The map's title over it */
  title: string
  /** What it shows, in a sentence or two */
  about: string
}

/** Each map's label in the list, its title, and what it shows, temperatures in the reader's units */
export function climateMapText(map: ClimateMap, units: Units): ClimateMapText {
  const t = (fahrenheit: number) => temperatureText(fahrenheit, units)
  switch (map) {
    case 'degree-days':
      return {
        label: 'Degree days since January 1',
        title: 'Degree days since January 1 against normal',
        about: `Growing degree days (modified, base ${t(50)}, upper ${t(86)}) from January 1 through the latest day, above or below the normal for the same days. More than normal means a warmer season than usual so far.`,
      }
    case 'rain':
      return {
        label: 'Precipitation, last 30 days',
        title: 'Precipitation over the last 30 days against normal',
        about: 'Rain and melted snow over the last 30 days, above or below the normal for the same days.',
      }
    case 'highs':
      return {
        label: 'Average high, last 7 days',
        title: 'Average high over the last 7 days against normal',
        about: 'The average daily high temperature over the last 7 days, above or below the normal for the same days.',
      }
    case 'freeze-chance':
      return {
        label: `Chance of a hard freeze (${t(28)})`,
        title: `Chance of a hard freeze (${t(28)})`,
        about: `The share of past years with a hard freeze (${t(28)} or colder) after today in spring, or by today in fall.`,
      }
    case 'last-freeze':
      return {
        label: 'Last spring frost, typical date',
        title: `Last spring frost (${t(32)}), median date`,
        about: `The date by which the last spring frost (${t(32)} or colder) had come in half of past years.`,
      }
    case 'first-freeze':
      return {
        label: 'First fall frost, typical date',
        title: `First fall frost (${t(32)}), median date`,
        about: `The date by which the first fall frost (${t(32)} or colder) had come in half of past years.`,
      }
    case 'hot-days':
      return {
        label: `Days at or above ${t(90)}, June to September`,
        title: `Days at or above ${t(90)}, June to September, against normal`,
        about: `How many more or fewer days reached ${t(90)} or above from June 1 to September 30 than normal. Before mid-June, the map shows last summer.`,
      }
  }
}

const month = (today: string) => Number(today.slice(5, 7))

/** Whether the chance of a freeze today means something: in spring (March–June) and fall (August–November) */
export const freezeSeason = (today: string): boolean => {
  const m = month(today)
  return (m >= 3 && m <= 6) || (m >= 8 && m <= 11)
}

/** The maps offered on a day: the chance of a freeze only in spring and fall */
export function mapsFor(today: string): ClimateMap[] {
  return CLIMATE_MAPS.filter((id) => id !== 'freeze-chance' || freezeSeason(today))
}

/** The map a first visit shows: the season's degree days from April to October, else the last 30 days' rain */
export function defaultMap(today: string): ClimateMap {
  const m = month(today)
  return m >= 4 && m <= 10 ? 'degree-days' : 'rain'
}

/** The map shown: the view's if it's offered today, else the day's default */
export function mapShown(chosen: ClimateMap | null, today: string): ClimateMap {
  return chosen && mapsFor(today).includes(chosen) ? chosen : defaultMap(today)
}

/** The layer a map reads */
export const MAP_LAYERS: Record<ClimateMap, string> = {
  'degree-days': 'degree_days',
  rain: 'precipitation_sum',
  highs: 'air_temperature_max',
  'freeze-chance': 'freeze_chance',
  'last-freeze': 'freeze_dates',
  'first-freeze': 'freeze_dates',
  'hot-days': 'air_temperature_max',
}

/** The summer the hot days count: this year's once June has half a month in the archive, else last year's; through
 * September 30 or the latest day */
export function hotDaysSpan(latest: string): { start: string; end: string } {
  const year = Number(latest.slice(0, 4))
  const summer = latest >= `${year}-06-15` ? year : year - 1
  const end = `${summer}-09-30`
  return { start: `${summer}-06-01`, end: latest < end ? latest : end }
}

/**
 * The map explorer's view of a climate map, or null where the layer has no days yet. `today` is the grid's today
 * (the freeze chance's day), `period` the normals' period, `at` the place chosen (carried to the explorer).
 */
export function explorerView(args: {
  map: ClimateMap
  layer: Pick<LayerInfo, 'range'> | undefined
  today: string
  period: Period
  at?: LatLng | null
}): ExplorerView | null {
  const { map, layer, today, period } = args
  const base: ExplorerView = {
    ...defaults(VIEW_FIELDS),
    layer: MAP_LAYERS[map],
    period: mapPeriod(period),
    at: args.at ?? null,
  }
  const latest = layer?.range.last?.slice(0, 10) ?? null
  switch (map) {
    case 'degree-days':
      return { ...base, span: 'season', dd: DEFAULT_DD, climate: 'departure' }
    case 'rain':
      if (!latest) return null
      return { ...base, span: 'range', start: addDays(latest, -29), date: latest, stat: 'sum', climate: 'departure' }
    case 'highs':
      if (!latest) return null
      return { ...base, span: 'range', start: addDays(latest, -6), date: latest, stat: 'mean', climate: 'departure' }
    case 'freeze-chance':
      return { ...base, date: today, threshold: 28 }
    case 'last-freeze':
      return { ...base, output: 'last_spring_p50' }
    case 'first-freeze':
      return { ...base, output: 'first_fall_p50' }
    case 'hot-days': {
      if (!latest) return null
      const { start, end } = hotDaysSpan(latest)
      return { ...base, span: 'range', start, date: end, count: 'days_above_90', climate: 'departure' }
    }
  }
}

/** The map explorer's link to a view (`/map?layer=…`), its settings as its Share link writes them */
export function explorerUrl(view: ExplorerView): string {
  const query = toQuery(VIEW_FIELDS, view).toString().replaceAll('%2C', ',')
  return `${routes.map()}${query ? `?${query}` : ''}`
}

/** The map's period as the explorer takes it: the climate sections' quick switch (30, 10 or 5 years), else 30 */
export const mapPeriod = (period: Period): MapPeriod => (period === 'last10' || period === 'last5' ? period : 'last30')
