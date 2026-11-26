// Counts of days within bounds (D88) for "This month against normal" (track 6.2): nine of the stored set, with
// their thresholds named in the reader's units, and the two answers they're read from: `/climate/compare` with
// `count=` (this month's running count against last year's and the normal) and `/climate/normals` with `count=` and
// `interval=month` (a typical year by month). Values stay as the API gives them (days); thresholds are kept in the
// units the pages ask in (`units=us`: °F and inches).

import type { TableResponse } from '@/types/api'

import type { CompareTable } from '../charts/climateCharts'
import type { Units } from '../units'
import { temperatureText } from './words'

export type DayCount = {
  variable: 'air_temperature_max' | 'air_temperature_min' | 'precipitation_sum'
  bound: 'above' | 'below'
  /** In °F or inches, as asked with `units=us` */
  value: number
}

/**
 * D88's set less sunlight and FACTS's 93.2 °F: hot days at the corn's upper threshold and at 90 °F, days that
 * stay below freezing, freeze and hard-freeze nights, warm nights, dry days and days of half an inch and an inch
 * of rain or more. Bounds include their value.
 */
export const DAY_COUNTS: readonly DayCount[] = [
  { variable: 'air_temperature_max', bound: 'above', value: 86 },
  { variable: 'air_temperature_max', bound: 'above', value: 90 },
  { variable: 'air_temperature_max', bound: 'below', value: 32 },
  { variable: 'air_temperature_min', bound: 'below', value: 32 },
  { variable: 'air_temperature_min', bound: 'below', value: 28 },
  { variable: 'air_temperature_min', bound: 'above', value: 70 },
  { variable: 'precipitation_sum', bound: 'below', value: 0.01 },
  { variable: 'precipitation_sum', bound: 'above', value: 0.5 },
  { variable: 'precipitation_sum', bound: 'above', value: 1 },
]

const valueText = (value: number) => String(value)

/** `count=`'s spec: `air_temperature_max:days_above_86` */
export const countSpec = (count: DayCount) => `${count.variable}:days_${count.bound}_${valueText(count.value)}`

/** The answer's column stem: `precipitation_sum_days_below_0p01` */
export const countColumn = (count: DayCount) =>
  `${count.variable}_days_${count.bound}_${valueText(count.value).replace('.', 'p')}`

/** The count's name in the reader's units: "Highs of 90 °F or more", "Days with 0.5 in of rain or more" */
export function countLabel(count: DayCount, units: Units): string {
  const more = count.bound === 'above' ? 'or more' : 'or less'
  if (count.variable === 'precipitation_sum') {
    const digits = units.system === 'metric' ? 1 : count.value < 0.1 ? 2 : count.value % 1 ? 1 : 0
    const amount = units.format('in', count.value, { digits })
    return count.bound === 'below'
      ? `Dry days (${amount} of precipitation or less)`
      : `Days with ${amount} of precipitation ${more}`
  }
  const temperature = temperatureText(count.value, units)
  if (count.variable === 'air_temperature_max') {
    return count.bound === 'below' ? `Days that stay at or below ${temperature}` : `Highs of ${temperature} ${more}`
  }
  return count.bound === 'above' ? `Warm nights (lows of ${temperature} or more)` : `Lows of ${temperature} ${more}`
}

/** Where a count ranks among the period's years, in words (a count's ties make "near normal" common) */
export function countWords(percentile: number | null | undefined): string {
  if (percentile === null || percentile === undefined) return '—'
  if (percentile <= 10) return 'Among the fewest'
  if (percentile < 33) return 'Fewer than usual'
  if (percentile <= 67) return 'Near normal'
  if (percentile < 90) return 'More than usual'
  return 'Among the most'
}

export type CountRow = {
  count: DayCount
  /** This year's count through `asOf` */
  now: number | null
  normal: number | null
  low: number | null
  high: number | null
  lastYear: number | null
  percentile: number | null
  missingDays: number
}

/** Each count's row as of the compare's last observed day (`asOf`); all null where none is observed yet */
export function countRows(table: CompareTable, counts: readonly DayCount[] = DAY_COUNTS): CountRow[] {
  const index = table.asOf ? table.dates.indexOf(table.asOf) : -1
  const at = (name: string) => (index >= 0 ? (table.values[name]?.[index] ?? null) : null)
  return counts.map((count) => {
    const column = countColumn(count)
    const total = table.totals[column]
    return {
      count,
      now: at(`${column}_cum`),
      normal: at(`${column}_cum_normal`),
      low: at(`${column}_cum_normal_p10`),
      high: at(`${column}_cum_normal_p90`),
      lastYear: at(`${column}_cum_last_year`),
      percentile: index >= 0 ? (total?.percentile ?? null) : null,
      missingDays: total?.missing_days ?? 0,
    }
  })
}

export type CountMonths = {
  /** `2026-01` … `2026-12` */
  months: string[]
  /** By column stem, the normal count per month */
  values: Record<string, (number | null)[]>
}

/** `/climate/normals?count=…&interval=month`: each count's normal per month */
export function countMonths(body: Pick<TableResponse, 'data'>): CountMonths {
  const data = (Array.isArray(body.data) ? {} : body.data) as Record<string, (number | string | null)[]>
  const months = (data.month ?? []) as string[]
  const values: Record<string, (number | null)[]> = {}
  for (const [name, column] of Object.entries(data)) {
    if (name === 'month' || name === 'point') continue
    values[name] = column.map((v) => (typeof v === 'number' ? v : null))
  }
  return { months, values }
}

/** A count of days as shown: a whole number, or a tenth where it's an average ("2.3") */
export function daysText(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return '—'
  return value.toFixed(digits)
}
