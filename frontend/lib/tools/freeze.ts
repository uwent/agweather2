// The freeze tool (`/tools/freeze`, track 5): a year's last spring and first fall freeze at a place against the
// period's typical dates, in words and a row per threshold; the chance of a freeze after or by a date; the
// thresholds to ask for (32, 28 and 24 °F, a crop's killing freeze or the reader's own); and the links to the same
// thresholds on the map. Pure functions over answers already parsed (`lib/charts/climateCharts.ts`), all in °F.

import type { FreezeChances, FreezeDates, FreezeRow } from '../charts/climateCharts'
import { daysBetween, formatDate } from '../dates'
import { monthDay } from '../models/format'
import { routes } from '../routes'
import type { Units } from '../units'
import type { Period } from '../climate/periods'
import { DEFAULT_PERIOD } from '../climate/periods'
import { FREEZE_THRESHOLDS_F, chanceWords, shareOfYears, temperatureText, thresholdName } from '../climate/words'
import type { TableResponse } from '@/types/api'

type Body = Pick<TableResponse, 'meta' | 'data'>
type Columns = Record<string, unknown[]>
const columnsOf = (body: Body): Columns => (Array.isArray(body.data) ? {} : (body.data as Columns))

// --- The thresholds

/** Which thresholds the tool asks for: the three named ones, a crop's killing freeze, or the reader's own */
export type ThresholdChoice = 'standard' | 'crop' | 'custom'

/** A crop's killing freeze, from `/degree-days/presets` (the presets with a `freeze`) */
export type CropFreeze = {
  id: string
  label: string
  /** °F */
  fahrenheit: number
  note: string | null
  citations: { text: string; url: string | null }[]
}

type PresetLike = {
  id: string
  label: string
  freeze?: {
    temperature: { us: number }
    note?: string | null
    citations?: { text: string; url?: string | null }[]
  } | null
}

/** The presets with a killing freeze, by label */
export function cropFreezes(presets: readonly PresetLike[]): CropFreeze[] {
  return presets
    .filter((p) => p.freeze)
    .map((p) => ({
      id: p.id,
      label: p.label,
      fahrenheit: p.freeze!.temperature.us,
      note: p.freeze!.note ?? null,
      citations: (p.freeze!.citations ?? []).map((c) => ({ text: c.text, url: c.url ?? null })),
    }))
    .sort((a, b) => a.label.localeCompare(b.label))
}

/** The lowest and highest temperature a reader may ask about, °F */
export const CUSTOM_RANGE_F = { min: -20, max: 40 } as const

/** The thresholds a choice asks for, °F, warmest first; null while a crop or a temperature is still to be chosen */
export function thresholdsFor({
  choice,
  crop,
  custom,
}: {
  choice: ThresholdChoice
  crop: CropFreeze | null
  custom: number | null
}): number[] | null {
  if (choice === 'crop') return crop ? [crop.fahrenheit] : null
  if (choice === 'custom') {
    if (custom === null || custom < CUSTOM_RANGE_F.min || custom > CUSTOM_RANGE_F.max) return null
    return [Math.round(custom * 10) / 10]
  }
  return [...FREEZE_THRESHOLDS_F]
}

/** "frost (32 °F)", "hard freeze (28 °F)", or "freeze at 30 °F or colder" */
export function freezeNoun(fahrenheit: number, units: Units): string {
  const name = thresholdName(fahrenheit)
  const temperature = temperatureText(fahrenheit, units)
  return name ? `${name.toLowerCase()} (${temperature})` : `freeze at ${temperature} or colder`
}

const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1)

// --- A year's own dates (`/freeze`)

export type OwnFreeze = { spring: string | null; fall: string | null }

/** Where a year stands: a past year is over; this year is in spring until July 1, then in fall */
export type Stage = 'past' | 'spring' | 'fall'

export function stageOf(year: number, today: string): Stage {
  if (year < Number(today.slice(0, 4))) return 'past'
  return today.slice(5) < '07-01' ? 'spring' : 'fall'
}

/** Whether an answer's dates come from Open-Meteo rather than our own grid (a year before our archive) */
export const fromOpenMeteo = (body: Body | null | undefined): boolean => !!body?.meta?.sources?.includes('openmeteo')

/** The forecast's coldest day from today on (`/weather/daily`'s `air_temperature_min`, °F) */
export function coldestLow(body: Body | null | undefined, today: string): { date: string; fahrenheit: number } | null {
  if (!body) return null
  const data = columnsOf(body)
  const dates = (data.date ?? []) as string[]
  const lows = (data.air_temperature_min ?? []) as (number | null)[]
  let found: { date: string; fahrenheit: number } | null = null
  dates.forEach((date, i) => {
    const low = lows[i]
    if (date < today || typeof low !== 'number') return
    if (!found || low < found.fahrenheit) found = { date, fahrenheit: low }
  })
  return found
}

/** The frost-free season's length in a year, days: from its last spring freeze to its first fall freeze (a season
 * without one counts from January 1 or to the year's end, as `/climate/frost` counts). This year in fall without a
 * fall freeze yet, the days so far; this year before July, null. */
export function seasonLength(own: OwnFreeze, year: number, today: string): { days: number; soFar: boolean } | null {
  const stage = stageOf(year, today)
  if (stage === 'spring') return null
  const start = own.spring ?? `${year}-01-01`
  if (own.fall) return { days: daysBetween(start, own.fall), soFar: false }
  if (stage === 'fall') return { days: daysBetween(start, today), soFar: true }
  return { days: daysBetween(start, `${year + 1}-01-01`), soFar: false }
}

// --- Against the typical date

/** Days from the typical date (given in any year: only its month and day count) to the year's own; + is later */
export function daysFromTypical(own: string, typical: string): number {
  return daysBetween(`${own.slice(0, 4)}${typical.slice(4, 10)}`, own)
}

/** "6 days later than the typical date, April 17", "the typical date, April 17" */
function againstTypical(own: string, typical: string | null | undefined): string {
  if (!typical) return ''
  const days = daysFromTypical(own, typical)
  const when = monthDay(typical.slice(5, 10))
  if (days === 0) return `, the typical date (${when})`
  const n = Math.abs(days)
  return `, ${n} day${n === 1 ? '' : 's'} ${days > 0 ? 'later' : 'earlier'} than typical (${when})`
}

/** "April 7" (this year), "April 7, 2010" (another) */
const dayIn = (iso: string, year: number, today: string) =>
  year === Number(today.slice(0, 4)) ? monthDay(iso.slice(5, 10)) : `${monthDay(iso.slice(5, 10))}, ${year}`

/**
 * The answer in a sentence or two, for one threshold: this year's last spring freeze so far (before July) or first
 * fall freeze (from July) against the typical date, with the forecast's coldest low while there's none; a past
 * year's both. `typical` is the threshold's row from `/climate/frost` (null while it loads, or outside our area).
 */
export function freezeAnswer({
  fahrenheit,
  own,
  typical,
  year,
  today,
  units,
  coldest,
}: {
  fahrenheit: number
  own: OwnFreeze
  typical: FreezeRow | null
  year: number
  today: string
  units: Units
  coldest: { date: string; fahrenheit: number } | null
}): string {
  const noun = freezeNoun(fahrenheit, units)
  const stage = stageOf(year, today)
  const coming = (date: string) => date > today
  const coldestText = coldest
    ? ` The coldest low in the forecast is ${temperatureText(coldest.fahrenheit, units)}, on ${formatDate(coldest.date, { weekday: true })}.`
    : ''

  if (stage === 'past') {
    const spring = own.spring
      ? `the last ${noun} of spring came on ${monthDay(own.spring.slice(5, 10))}${againstTypical(own.spring, typical?.lastSpring[50])}`
      : `there was no ${noun} in spring`
    const fall = own.fall
      ? `the first of fall came on ${monthDay(own.fall.slice(5, 10))}${againstTypical(own.fall, typical?.firstFall[50])}`
      : `there was none in fall`
    return `In ${year}, ${spring}, and ${fall}.`
  }

  if (stage === 'spring') {
    const usual = typical?.lastSpring[50]
      ? ` In half the years the last came by ${monthDay(typical.lastSpring[50].slice(5, 10))}${typical.lastSpring[90] ? `, and in ${shareOfYears(10)} after ${monthDay(typical.lastSpring[90].slice(5, 10))}` : ''}.`
      : ''
    if (!own.spring) return `There has been no ${noun} yet this year.${usual}${coldestText}`
    const verb = coming(own.spring) ? 'is forecast for' : 'came on'
    return `This spring’s latest ${noun} so far ${verb} ${dayIn(own.spring, year, today)}.${usual}${coldestText}`
  }

  if (own.fall) {
    const verb = coming(own.fall) ? 'is forecast for' : 'came on'
    return `This fall’s first ${noun} ${verb} ${dayIn(own.fall, year, today)}${againstTypical(own.fall, typical?.firstFall[50])}.`
  }
  const median = typical?.firstFall[50]
  const ago = median ? daysBetween(`${year}${median.slice(4, 10)}`, today) : 0
  const usual = median
    ? ` In half the years the first came by ${monthDay(median.slice(5, 10))}${ago > 0 ? `, ${ago} day${ago === 1 ? '' : 's'} ago` : ''}.`
    : ''
  return `There has been no ${noun} yet this fall.${usual}${coldestText}`
}

// --- Look up a date (`/climate/frost/chances`)

export type LookUp = {
  /** The date asked, in the chances' year */
  date: string
  season: 'spring' | 'fall'
  /** By threshold (°F): the chance in percent, null where there's none to give */
  chances: { fahrenheit: number; chance: number | null }[]
}

/** The chance of each threshold or colder after the date (January–June) or by it (July–December); null for a date
 * the chances don't hold */
export function lookUp(chances: FreezeChances, date: string): LookUp | null {
  let mmdd = date.slice(5, 10)
  let i = chances.dates.findIndex((d) => d.slice(5, 10) === mmdd)
  if (i < 0 && mmdd === '02-29') {
    mmdd = '02-28'
    i = chances.dates.findIndex((d) => d.slice(5, 10) === mmdd)
  }
  if (i < 0) return null
  const toF = (t: number) => (chances.unit === 'degC' ? Math.round((t * 9) / 5 + 32) : t)
  return {
    date: chances.dates[i],
    season: chances.season[i],
    chances: chances.thresholds.map((t) => ({ fahrenheit: toF(t), chance: chances.chance[String(t)]?.[i] ?? null })),
  }
}

/** A lookup's sentence for one threshold: "A frost (32 °F) came after May 1 in 35% of years." */
export function lookUpWords(
  found: { fahrenheit: number; chance: number | null },
  date: string,
  season: 'spring' | 'fall',
  units: Units,
): string {
  const noun = freezeNoun(found.fahrenheit, units)
  const when = monthDay(date.slice(5, 10))
  if (found.chance === null) return `${capital(noun)}: not enough years with data to say.`
  const chance = Math.round(found.chance)
  if (season === 'spring') {
    if (chance <= 0) return `No year had a ${noun} after ${when}.`
    if (chance >= 100) return `Every year had a ${noun} after ${when}.`
    return `A ${noun} came after ${when} in ${chanceWords(chance)}.`
  }
  if (chance <= 0) return `No year had had its first ${noun} by ${when}.`
  if (chance >= 100) return `Every year had had its first ${noun} by ${when}.`
  return `The first ${noun} had come by ${when} in ${chanceWords(chance)}.`
}

// --- The rows

export type ToolRow = {
  fahrenheit: number
  own: OwnFreeze | null
  typical: FreezeRow | null
  season: { days: number; soFar: boolean } | null
}

/** A row per threshold asked for, warmest first, with the year's dates and the period's where they've come */
export function toolRows({
  thresholds,
  own,
  dates,
  year,
  today,
}: {
  thresholds: number[]
  own: Map<number, OwnFreeze> | null
  dates: FreezeDates | null
  year: number
  today: string
}): ToolRow[] {
  return thresholds.map((fahrenheit) => {
    const mine = own?.get(fahrenheit) ?? null
    return {
      fahrenheit,
      own: mine,
      typical: dates?.rows.find((row) => row.fahrenheit === fahrenheit) ?? null,
      season: mine ? seasonLength(mine, year, today) : null,
    }
  })
}

// --- The map

/** The map holds freeze odds and dates for these thresholds only, °F */
export const MAP_THRESHOLDS_F: readonly number[] = FREEZE_THRESHOLDS_F

/** The map's threshold for the tool's: the same where the map holds it, else the nearest it holds */
export function mapThreshold(fahrenheit: number): number {
  return [...MAP_THRESHOLDS_F].sort((a, b) => Math.abs(a - fahrenheit) - Math.abs(b - fahrenheit) || b - a)[0]
}

/** The map of freeze dates (`freeze_dates`, the typical date of the season in view) or of the chance of a freeze on
 * a date (`freeze_chance`), at the threshold and period, centered on the place */
export function freezeMapUrl({
  layer,
  fahrenheit,
  period,
  season,
  date,
  at,
}: {
  layer: 'freeze_dates' | 'freeze_chance'
  fahrenheit: number
  period: Period
  season: 'spring' | 'fall'
  date?: string | null
  at: { lat: number; lng: number } | null
}): string {
  const query = new URLSearchParams({ layer })
  if (layer === 'freeze_dates') query.set('output', season === 'spring' ? 'last_spring_p50' : 'first_fall_p50')
  if (layer === 'freeze_chance' && date) query.set('date', date)
  query.set('threshold', String(mapThreshold(fahrenheit)))
  if (period !== DEFAULT_PERIOD) query.set('period', period)
  if (at) query.set('at', `${Number(at.lat.toFixed(4))},${Number(at.lng.toFixed(4))}`)
  return `${routes.map()}?${query.toString().replaceAll('%2C', ',')}`
}
