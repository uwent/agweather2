// The API's columnar table (`{meta, data}` with `data` a list per column, D117) as rows a chart or table reads:
// one `Day` a row (a day, or an hour on the hourly endpoints), with its kind and, per column, whether the value
// is an estimate or missing. Values stay in the units the answer gives (`meta.units`), named here by their unit
// symbol so `lib/units` converts them at display: a page asks for `units=metric` once and a switch of units
// redraws without a request.

import type { Location, TableResponse } from '@/types/api'

import { UNITS } from './units'

/** observed: a whole day (or hour) of analysis; partial: today, observed so far and forecast for the rest;
 * forecast: the forecast; projection: past years' weather after the forecast (a model's extended outlook) */
export type Kind = 'observed' | 'partial' | 'forecast' | 'projection'

export type Day = {
  /** The row's date (`2026-11-25`), or its hour in UTC (`2026-11-25T14:00Z`) on hourly endpoints */
  date: string
  kind: Kind
  /** Each numeric column's value, null where it's missing */
  values: Record<string, number | null>
  /** Columns whose value this day is an estimate (the API's `<column>_estimated`) */
  estimated: ReadonlySet<string>
  /** Columns without a value this day: null, or the API's `<column>_missing` */
  missing: ReadonlySet<string>
}

export type Table = {
  days: Day[]
  /** Each numeric column's unit symbol (`degC`, `km_h`, `mm`); a unitless column (an index, a count) has none */
  units: Record<string, string>
  /** The API's own notes, public sentences shown as they are */
  warnings: string[]
  location: Location | null
  /** Whether the rows are hours */
  hourly: boolean
}

const KINDS: readonly Kind[] = ['observed', 'partial', 'forecast', 'projection']
// Columns that describe a row rather than measure something
const KEYS = new Set(['date', 'time', 'kind', 'point', 'local_time'])
const FLAG = /_(estimated|missing)$/

/** Whether a day is (at least partly) forecast: today's partial day counts, since its hours ahead are */
export const isForecast = (day: Pick<Day, 'kind'>) => day.kind === 'forecast' || day.kind === 'partial'

/** The unit symbol for a label the API gives in `meta.units` ("°C", "km/h", "m³/m³"). A difference of
 * temperatures (a dew point depression) has the same label as a temperature: `column` tells them apart. */
export function unitSymbol(label: string, column = ''): string | null {
  if (label === '') return null
  if (/depression/.test(column)) {
    if (label === '°C') return 'delta_degC'
    if (label === '°F') return 'delta_degF'
  }
  for (const [symbol, unit] of Object.entries(UNITS)) {
    if (unit.label === label && !symbol.startsWith('delta_')) return symbol
  }
  return null
}

/** An answer's columns as the API sends them (`orient=columns`), a list per column */
export type Columns = Record<string, (number | string | boolean | null)[]>

/** The columns of an answer, or none when it came as rows */
export const columnsOf = (body: Pick<TableResponse, 'data'>): Columns =>
  Array.isArray(body.data) ? {} : (body.data as Columns)

/** The answer's rows, oldest first */
export function tableRows(body: Pick<TableResponse, 'meta' | 'data'>): Table {
  const data = body.data as Record<string, (number | string | boolean | null)[]>
  const times = (data.date ?? data.time ?? []) as string[]
  const hourly = !data.date && !!data.time
  // A table without kinds (a model run's inputs on your weather) is all observed
  const kinds = (data.kind ?? times.map(() => 'observed')) as (string | null)[]
  const columns = Object.keys(data).filter((name) => !KEYS.has(name) && !FLAG.test(name))
  const numeric = columns.filter((name) => data[name].every((value) => value === null || typeof value === 'number'))

  const units: Record<string, string> = {}
  for (const name of numeric) {
    const symbol = unitSymbol(body.meta.units[name] ?? '', name)
    if (symbol) units[name] = symbol
  }

  const days: Day[] = []
  times.forEach((date, i) => {
    // A row without a kind is past the forecast's end (the API keeps the days asked for): nothing to show
    const kind = kinds[i]
    if (!KINDS.includes(kind as Kind)) return
    const values: Record<string, number | null> = {}
    const estimated = new Set<string>()
    const missing = new Set<string>()
    for (const name of numeric) {
      const value = data[name][i] as number | null
      values[name] = value
      if (data[`${name}_estimated`]?.[i] === true) estimated.add(name)
      if (value === null || data[`${name}_missing`]?.[i] === true) missing.add(name)
    }
    days.push({ date, kind: kind as Kind, values, estimated, missing })
  })

  return { days, units, warnings: body.meta.warnings ?? [], location: body.meta.location ?? null, hourly }
}

/** How many rows a column is estimated on, and missing on */
export function flagCounts(days: Day[], column: string): { estimated: number; missing: number } {
  let estimated = 0
  let missing = 0
  for (const day of days) {
    if (day.estimated.has(column)) estimated += 1
    if (day.missing.has(column)) missing += 1
  }
  return { estimated, missing }
}
