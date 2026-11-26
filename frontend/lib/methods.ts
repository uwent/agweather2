// Words for the methods page (`/methods`, track 4): its sources by use, scores in the reader's units, clock hours,
// date spans and the anchors other pages link to (`/methods#variable-air_temperature_min`). The facts come from the
// page's props, which come from the code (web.methodspage, D92).

import { longDate } from '@/lib/models/format'
import { convert, displayUnit, UNITS, type UnitSystem } from '@/lib/units'
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
