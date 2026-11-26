// Words for a model's page and catalog (track 4): dates written out, lists joined in prose, units by the reader's
// system, and the links to the model's map and to the model at a site.

import { displayUnit, UNITS, type UnitSystem } from '@/lib/units'

const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
]

/** "July 1" for "07-01" (a spec's MM-DD) */
export function monthDay(mmdd: string): string {
  const [month, day] = mmdd.split('-').map(Number)
  return `${MONTHS[month - 1]} ${day}`
}

/** "November 18, 2026" for "2026-11-18" */
export function longDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split('-').map(Number)
  return `${MONTHS[month - 1]} ${day}, ${year}`
}

/** "a", "a and b", "a, b and c" */
export function andList(items: string[]): string {
  if (items.length <= 2) return items.join(' and ')
  return `${items.slice(0, -1).join(', ')} and ${items[items.length - 1]}`
}

/** "From July 1 to August 15 each year"; a season over New Year says so */
export function seasonText(season: string[] | null, opens: string | null = null): string {
  if (!season) return 'All year.'
  const [first, last] = season
  if (opens)
    return `Its season opens at each location ${opens}, and runs to ${monthDay(last)}. Where we don’t have the 30-year normal temperatures, it opens on ${monthDay(first)}.`
  const across = last < first ? ', into the next year' : ''
  return `From ${monthDay(first)} to ${monthDay(last)} each year${across}.`
}

/** The label of the unit a value stored in `symbol` is shown in ('°F·d'), or '' for an index or an unknown unit */
export function unitLabel(symbol: string, system: UnitSystem): string {
  if (!UNITS[symbol]) return ''
  return UNITS[displayUnit(symbol, system)]?.label ?? ''
}

/** The map explorer on the model's layer, as a shared link opens it (lib/explorer/view.ts reads `layer`) */
export function modelMapUrl(layer: string): string {
  return `/map?${new URLSearchParams({ layer })}`
}

/** A model at a site (track 3 step 6), by the site's key (`43.07,-89.4`) */
export function siteModelUrl(siteKey: string, modelId: string): string {
  return `/sites/${siteKey}/models/${encodeURIComponent(modelId)}`
}

/** How a check was made, as a heading for it */
export const CHECK_KINDS: Record<string, string> = {
  published: 'Against its sources’ own numbers',
  system: 'Against another system on the same weather',
  observations: 'Against observations in the field',
}
