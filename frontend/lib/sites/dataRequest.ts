// A site's Data tab (track 3 step 10) and /data's weather at locations (track 7 step 7.1): a download builder for one point or several. The reader picks what (hourly or daily
// weather, totals over the days, degree days or a model run), the variables (from `/variables`, grouped), the days,
// the units and CSV or JSON; the tab shows the request's URL for a script, and says before the download fails when
// the request is larger than the API takes (its limits, `app/api/routes/weather.py`'s MAX_DAYS and MAX_HOURS).

import type { VariableInfo } from '@/types/api'

import { apiUrl } from '../api'
import { addDays, daysBetween, formatDate } from '../dates'
import { formatNumber } from '../units'

export type DataKind = 'daily' | 'hourly' | 'totals' | 'degree-days' | 'model'

/** The API's limits on one request (app/api/routes/weather.py, api/params.py; web/tests/test_datapage.py holds
 * them to the server's) */
export const MAX_DAYS = 3660
export const MAX_HOURS = 2 * 8784
export const MAX_ROWS = 100_000
export const MAX_POINTS = 50

export const KINDS: { value: DataKind; label: string; description: string }[] = [
  { value: 'daily', label: 'Daily weather', description: 'A row per day: highs, lows, means, totals and hour counts.' },
  { value: 'hourly', label: 'Hourly weather', description: 'A row per hour, times in UTC, up to about two years.' },
  {
    value: 'totals',
    label: 'Totals',
    description: 'One row: each amount added up over the days, with any missing or estimated days counted.',
  },
  {
    value: 'degree-days',
    label: 'Degree days',
    description: 'A row per day: each setting’s degree days and running total.',
  },
  {
    value: 'model',
    label: 'A model run',
    description: 'A row per day: the model’s inputs, its outputs and its risk.',
  },
]

export const DEFAULT_VARS: Record<'daily' | 'hourly' | 'totals', string[]> = {
  daily: ['air_temperature_min', 'air_temperature_max', 'precipitation_sum'],
  hourly: ['air_temperature', 'relative_humidity', 'precipitation'],
  totals: ['precipitation_sum', 'et0_sum'],
}

/** Whether a daily variable adds up over days (`/weather/totals` takes it): daily totals, hour counts, Utah chill
 * units and the water balance, as `agdata.computed.adds_up` says */
export function addsUp(variable: Pick<VariableInfo, 'name' | 'statistic' | 'unit'>): boolean {
  return (
    variable.statistic === 'sum' ||
    variable.unit === 'hour' ||
    variable.unit === 'chill_units' ||
    variable.name === 'water_balance'
  )
}

/** The variables a kind of download takes */
export function variablesFor(kind: DataKind, variables: VariableInfo[]): VariableInfo[] {
  if (kind === 'hourly') return variables.filter((v) => v.kind === 'hourly')
  if (kind === 'daily') return variables.filter((v) => v.kind === 'daily')
  if (kind === 'totals') return variables.filter((v) => v.kind === 'daily' && addsUp(v))
  return []
}

// Groups by what a variable measures, first match wins
const GROUPS: [string, RegExp][] = [
  ['Humidity', /relative_humidity|^hours_rh|_rh_|dew_point_depression/],
  ['Temperature', /^air_temperature|^dew_point/],
  ['Precipitation and evapotranspiration', /precip|^et0|water_balance/],
  ['Wind and pressure', /wind|pressure/],
  ['Sun and clouds', /shortwave|cloud/],
  ['Soil', /soil/],
  ['Snow', /snow/],
  ['Heat and chill', /^hours_temperature|degree_hours|chill|^thi|^hours_thi|^cci/],
]
export const OTHER_GROUP = 'Model inputs'
// The order groups are shown in: temperature first
const SHOWN = ['Temperature', ...GROUPS.map(([label]) => label).filter((label) => label !== 'Temperature'), OTHER_GROUP]

/** The variables grouped, in the catalog's order within each group, groups without variables left out */
export function groupVariables(variables: VariableInfo[]): { label: string; variables: VariableInfo[] }[] {
  const groups = new Map<string, VariableInfo[]>(SHOWN.map((label) => [label, []]))
  for (const v of variables) {
    const label = GROUPS.find(([, pattern]) => pattern.test(v.name))?.[0] ?? OTHER_GROUP
    groups.get(label)!.push(v)
  }
  return [...groups].filter(([, list]) => list.length).map(([label, list]) => ({ label, variables: list }))
}

export type DataChoice = {
  kind: DataKind
  vars: string[]
  /** YYYY-MM-DD */
  start: string
  /** YYYY-MM-DD; ignored with `forecast` */
  end: string
  /** Through the forecast (the API's default end) rather than to `end` */
  forecast: boolean
  units: 'us' | 'metric'
  format: 'csv' | 'json'
  /** Degree-day settings, `dd=` text in the request's units */
  dd: string
  /** Degree days' or a model's start of counting, YYYY-MM-DD, or '' for its default */
  biofix: string
  model: string
}

export type DataRequest = {
  path: string
  params: Record<string, string | number | boolean | null>
  /** The URL, from the site's root */
  url: string
  /** Why the API would refuse it, in its words, or null */
  problem: string | null
}

/** A location as the API takes it */
export type Point = { lat: number; lng: number }

/** The request for a choice at a point, and whether the API takes it */
export function dataRequest(choice: DataChoice, lat: number, lng: number, today: string): DataRequest {
  return pointsRequest(choice, [{ lat, lng }], today)
}

/** The request for a choice at one location (`lat` and `lng`) or several (`points=lat,lng;lat,lng`, as /data
 * builds it), and whether the API takes it */
export function pointsRequest(choice: DataChoice, points: Point[], today: string): DataRequest {
  const { kind } = choice
  const path =
    kind === 'model' ? `/models/${choice.model}/run` : kind === 'degree-days' ? '/degree-days' : `/weather/${kind}`
  const hourly = kind === 'hourly'
  const one = points.length === 1 ? points[0] : null
  const params: DataRequest['params'] = {
    lat: one?.lat ?? null,
    lng: one?.lng ?? null,
    points: one ? null : points.map((p) => `${p.lat},${p.lng}`).join(';') || null,
    start: choice.start,
    end: choice.forecast ? null : hourly ? `${choice.end}T23` : choice.end,
    forecast: choice.forecast ? null : false,
    units: choice.units,
    format: choice.format,
  }
  if (kind === 'daily' || kind === 'hourly' || kind === 'totals') params.vars = choice.vars.join(',') || null
  if (kind === 'degree-days') params.dd = choice.dd.replace(/\s+/g, '') || null
  if ((kind === 'degree-days' || kind === 'model') && choice.biofix) params.biofix = choice.biofix
  return { path, params, url: apiUrl(path, params), problem: sizeProblem(choice, today, points.length) }
}

/** The days a choice covers through its last day (the forecast's, about 16 days ahead, with `forecast`), or null
 * while its dates are incomplete or backwards */
export function choiceDays(choice: DataChoice, today: string): number | null {
  const last = choice.forecast ? addDays(today, 16) : choice.end
  if (!choice.start || !last || last < choice.start) return null
  return daysBetween(choice.start, last) + 1
}

/** About how large a download is, in bytes: measured on the API's CSV (a row ~20 bytes and ~8 a value) and JSON
 * (a tenth more), with its description at the top */
export function downloadBytes(choice: DataChoice, today: string, points: number): number | null {
  const days = choiceDays(choice, today)
  if (days === null) return null
  const steps = choice.kind === 'totals' ? 1 : choice.kind === 'hourly' ? days * 24 : days
  const columns =
    choice.kind === 'model'
      ? 10
      : choice.kind === 'degree-days'
        ? 2 * Math.max(1, choice.dd.split(',').filter((s) => s.trim()).length) + 2
        : Math.max(1, choice.vars.length) * (choice.kind === 'totals' ? 3 : 1)
  const csv = 3000 + steps * points * (20 + 8 * columns)
  return choice.format === 'json' ? Math.round(csv * 1.1 + 500 * points) : csv
}

/** A size in bytes as a reader says it: "about 40 KB", "about 2.5 MB" */
export function formatBytes(bytes: number): string {
  if (bytes < 1000) return 'under 1 KB'
  if (bytes < 1e6) return `about ${formatNumber(Math.round(bytes / 1000))} KB`
  if (bytes < 1e9) return `about ${twoFigures(bytes / 1e6)} MB`
  return `about ${twoFigures(bytes / 1e9)} GB`
}

/** 2.48 → "2.5", 21.4 → "21", 140 → "140" */
function twoFigures(value: number): string {
  const rounded = Number(value.toPrecision(2))
  return rounded.toLocaleString('en-US', { maximumFractionDigits: rounded < 10 ? 1 : 0 })
}

/** The API's refusal of a choice too large, said before it's sent; null when it fits. `points`: the locations
 * asked for (one on a site's page). */
export function sizeProblem(choice: DataChoice, today: string, points = 1): string | null {
  if (points < 1) return 'Choose at least one location.'
  if (points > MAX_POINTS)
    return `You chose ${formatNumber(points)} locations; a request can include up to ${MAX_POINTS}. Remove some, or download them in several requests.`
  if (!choice.start) return 'Enter a start date.'
  // The forecast reaches about 16 days ahead
  const last = choice.forecast ? addDays(today, 16) : choice.end
  if (!last) return 'Enter an end date, or include the forecast.'
  if (last < choice.start)
    return 'The end date is before the start date. Choose an end date on or after the start date.'
  if ((choice.kind === 'daily' || choice.kind === 'hourly' || choice.kind === 'totals') && !choice.vars.length)
    return 'Choose at least one variable.'
  if (choice.kind === 'degree-days' && !choice.dd.trim()) return 'Enter at least one degree-day setting.'
  if (choice.kind === 'model' && !choice.model) return 'Choose a model.'
  const days = daysBetween(choice.start, last) + 1
  if (choice.kind === 'hourly' && days * 24 > MAX_HOURS)
    return `This request covers ${formatNumber(days * 24)} hours (${formatDate(choice.start, { year: true })} to ${formatDate(last, { year: true })}); a request can include up to ${formatNumber(MAX_HOURS)}, about two years. Choose a shorter period, or download days instead.`
  if (days > MAX_DAYS)
    return `This request covers ${formatNumber(days)} days; a request can include up to ${formatNumber(MAX_DAYS)}, about ten years. Choose a shorter period.`
  // The API counts a location's days (or hours) read, even for totals' one row
  const rows = (choice.kind === 'hourly' ? days * 24 : days) * points
  if (rows > MAX_ROWS)
    return `This request would return ${formatNumber(rows)} rows (${formatNumber(points)} locations); a request can return up to ${formatNumber(MAX_ROWS)}. Choose fewer locations or a shorter period.`
  return null
}
