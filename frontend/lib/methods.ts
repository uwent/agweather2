// Words for the methods page (`/methods`, track 4): its sources by use, scores in the reader's units, clock hours,
// date spans and the anchors other pages link to (`/methods#variable-air_temperature_min`). The facts come from the
// page's props, which come from the code (web.methodspage, D92).

import { longDate } from '@/lib/models/format'
import { routes } from '@/lib/routes'
import { convert, displayUnit, UNITS, type Units, type UnitSystem } from '@/lib/units'
import type { MethodsSource, MethodsVariable } from '@/types'

export type Role = MethodsSource['role']

/** The uses in the order the page lists them, each with its heading and a sentence on what it's for */
export const ROLES: { id: Role; name: string; about: string }[] = [
  {
    id: 'archive',
    name: 'The archive',
    about: 'The weather we keep for every hour on the map, the record that maps, sites and models read.',
  },
  {
    id: 'provisional',
    name: 'The newest hours',
    about: 'Quicker sources that fill the newest hours until the archive’s own arrive and replace them.',
  },
  {
    id: 'forecast',
    name: 'The forecast',
    about: 'The days ahead, on the same grid, which models and maps show after the observed days.',
  },
  {
    id: 'outside',
    name: 'Outside our area',
    about: 'Weather for locations outside the area our maps cover, and for dates before our archive.',
  },
  {
    id: 'normals',
    name: 'The 30-year normal',
    about: 'The years of the climate normal from before our archive begins.',
  },
]

/** The anchor of a variable's entry: a daily one (what models read) by its name, the others by kind and name */
export function variableAnchor(name: string, kind: MethodsVariable['kind'] = 'daily'): string {
  if (kind === 'daily') return `variable-${name}`
  return `variable-${kind === 'hourly' ? 'hourly' : 'total'}-${name}`
}

/** "6 p.m.", "noon", "midnight" for a clock hour (0–24) */
export function clockHour(hour: number): string {
  const h = ((hour % 24) + 24) % 24
  if (h === 0) return 'midnight'
  if (h === 12) return 'noon'
  return h < 12 ? `${h} a.m.` : `${h - 12} p.m.`
}

/** When a source fills the dates it's used for, in words, or '' when it always has */
export function dateSpan(first: string | null, last: string | null): string {
  if (first && last) return `From ${longDate(first)} through ${longDate(last)}.`
  if (first) return `From ${longDate(first)} on.`
  if (last) return `Through ${longDate(last)}.`
  return ''
}

/** A score in the reader's units with its unit label ("1.7 MJ/m²", "0.50 °F", "0.987"), three significant digits */
export function scoreText(value: number, unit: string, system: UnitSystem): string {
  if (!UNITS[unit]) return formatSignificant(value)
  const shown = displayUnit(unit, system)
  const converted = convert(value, unit, shown) ?? value
  const label = UNITS[shown]?.label ?? ''
  return label ? `${formatSignificant(converted)} ${label}` : formatSignificant(converted)
}

function formatSignificant(value: number): string {
  const text = Number(value.toPrecision(3)).toString()
  return text.replace('-', '−')
}

/** The variables of one kind, in the catalog's order */
export function ofKind(variables: MethodsVariable[], kind: MethodsVariable['kind']): MethodsVariable[] {
  return variables.filter((v) => v.kind === kind)
}

/** "6 km (1.6 mi)" */
export function kmText(km: number): string {
  return `${km} km (${(km / 1.609344).toFixed(1)} mi)`
}

// --- How normals are made (`/methods#normals`, step 6.5): words for the page's `normals` props ---

/** Where the climate pages' "How normals are made" links go */
export const normalsHref = (): string => `${routes.methods()}#normals`

/** A value stored in `unit`, in the reader's units, to three significant digits: "86 °F", "30 °C", "0.254 mm" */
export function valueText(value: number, unit: string, units: Units): string {
  return `${numberText(units.toDisplay(unit, value) ?? value)} ${units.label(unit)}`
}

const numberText = (value: number): string => Number(value.toPrecision(3)).toString().replace('-', '−')

/** Years in words, runs joined: "1996–2015", "2016, 2018–2020"; '' for none */
export function yearsText(years: readonly number[]): string {
  const sorted = [...years].sort((a, b) => a - b)
  const runs: string[] = []
  for (let k = 0; k < sorted.length;) {
    let end = k
    while (end + 1 < sorted.length && sorted[end + 1] === sorted[end] + 1) end++
    runs.push(end === k ? `${sorted[k]}` : `${sorted[k]}–${sorted[end]}`)
    k = end + 1
  }
  return runs.join(', ')
}

/** "10 years", "1 year" */
export const yearCount = (n: number): string => `${n} year${n === 1 ? '' : 's'}`

// The daily variables the normals keep, inside a sentence; any other by its catalog name
const DAILY_WORDS: Record<string, string> = {
  air_temperature_max: 'the daily high',
  air_temperature_min: 'the daily low',
  air_temperature_mean: 'the daily mean temperature',
  relative_humidity_max: 'the daily highest relative humidity',
  relative_humidity_min: 'the daily lowest relative humidity',
  precipitation_sum: 'daily precipitation',
  shortwave_radiation_sum: 'daily solar radiation',
  wind_speed_mean: 'the daily mean wind speed',
  et0_sum: 'daily reference evapotranspiration',
}

/** "the daily high" for air_temperature_max */
export function dailyWords(name: string, longName?: string): string {
  return DAILY_WORDS[name] ?? longName ?? name
}

const COUNT_SUBJECTS: Record<string, string> = {
  air_temperature_max: 'a high of',
  air_temperature_min: 'a low of',
  precipitation_sum: 'precipitation of',
  shortwave_radiation_sum: 'solar radiation of',
}

/** A count of days the normals keep, as a reader's phrase: "Days with a high of 86 °F or more" */
export function countText(
  count: { variable: string; above: number | null; below: number | null; unit: string },
  units: Units,
): string {
  const value = count.above ?? count.below
  if (value === null) return ''
  const subject = COUNT_SUBJECTS[count.variable] ?? `${dailyWords(count.variable)} of`
  return `Days with ${subject} ${valueText(value, count.unit, units)} or ${count.above !== null ? 'more' : 'less'}`
}

const DD_METHOD_WORDS: Record<string, string> = {
  sine: 'single sine',
  modified: 'modified average',
  average: 'simple average',
  average_capped_mean: 'simple average, the day’s mean capped at the upper threshold',
}

/** A degree-day setting in °F, in words: "modified average, 50 to 86 °F", "single sine, base 52 °F" */
export function settingText(method: string, base: number, upper: number | null, units: Units): string {
  const name = DD_METHOD_WORDS[method] ?? method
  if (upper === null) return `${name}, base ${valueText(base, 'degF', units)}`
  return `${name}, ${numberText(units.toDisplay('degF', base) ?? base)} to ${valueText(upper, 'degF', units)}`
}

/** Degree days stored in °F, in the reader's units, whole: "395 °F degree days", "219 °C degree days" */
export function degreeDaysText(ddF: number, units: Units): string {
  const shown = units.toDisplay('degF_day', ddF) ?? ddF
  return `${Math.round(shown).toLocaleString('en-US')} ${units.system === 'metric' ? '°C' : '°F'} degree days`
}

const TOTAL_WORDS: Record<string, string> = {
  precipitation: 'precipitation since January 1',
  et0: 'reference evapotranspiration since January 1',
}

/** A running total the normals keep percentiles of, in words: "precipitation since January 1", "single sine
 * degree days, 41 to 86 °F" (`dd_sine_41_86`) */
export function totalText(name: string, units: Units, longName?: string): string {
  const match = /^dd_(sine|modified|average)_([\dp.]+)(?:_([\dp.]+))?$/.exec(name)
  if (!match) return TOTAL_WORDS[name] ?? longName ?? name
  const number = (text: string) => Number(text.replace('p', '.'))
  const upper = match[3] === undefined ? null : number(match[3])
  return `degree days (${settingText(match[1], number(match[2]), upper, units)}) since January 1`
}
