// A site's Data tab (track 3 step 10): a download builder for one point. The reader picks what (hourly or daily
// weather, totals over the days, degree days or a model run), the variables (from `/variables`, grouped), the days,
// the units and CSV or JSON; the tab shows the request's URL for a script, and says before the download fails when
// the request is larger than the API takes (its limits, `app/api/routes/weather.py`'s MAX_DAYS and MAX_HOURS).

import type { VariableInfo } from '@/types/api'

import { apiUrl } from '../api'
import { addDays, daysBetween, formatDate } from '../dates'
import { formatNumber } from '../units'

export type DataKind = 'daily' | 'hourly' | 'totals' | 'degree-days' | 'model'

/** The API's limits on one request (app/api/routes/weather.py) */
export const MAX_DAYS = 3660
export const MAX_HOURS = 2 * 8784

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

/** The request for a choice at a point, and whether the API takes it */
export function dataRequest(choice: DataChoice, lat: number, lng: number, today: string): DataRequest {
  const { kind } = choice
  const path =
    kind === 'model' ? `/models/${choice.model}/run` : kind === 'degree-days' ? '/degree-days' : `/weather/${kind}`
  const hourly = kind === 'hourly'
  const params: DataRequest['params'] = {
    lat,
    lng,
    start: choice.start,
    end: choice.forecast ? null : hourly ? `${choice.end}T23` : choice.end,
    forecast: choice.forecast ? null : false,
    units: choice.units,
    format: choice.format,
  }
  if (kind === 'daily' || kind === 'hourly' || kind === 'totals') params.vars = choice.vars.join(',') || null
  if (kind === 'degree-days') params.dd = choice.dd.replace(/\s+/g, '') || null
  if ((kind === 'degree-days' || kind === 'model') && choice.biofix) params.biofix = choice.biofix
  return { path, params, url: apiUrl(path, params), problem: sizeProblem(choice, today) }
}

/** The API's refusal of a choice too large, said before it's sent; null when it fits */
export function sizeProblem(choice: DataChoice, today: string): string | null {
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
  return null
}
