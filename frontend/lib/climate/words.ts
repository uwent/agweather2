// The climate pages' sentences (CLAUDE.md, "Writing for the public"): what a percentile, a departure, a day ahead
// of normal or a freeze chance means, in words a grower reads at a glance. Pure functions over numbers already
// parsed (./../charts/climateCharts.ts), so the site's Climate tab, `/climate` and the tools say things alike.

import { formatDate } from '../dates'
import type { Units } from '../units'
import { plural } from '../words'

/** The thresholds named for freezes (Ben, 2026-11-26, track 6 Q5), in °F */
export const FREEZE_NAMES: Record<number, string> = { 32: 'Frost', 28: 'Hard freeze', 24: 'Killing freeze' }

/** The default thresholds, °F */
export const FREEZE_THRESHOLDS_F: readonly number[] = [32, 28, 24]

/** A temperature stored in °F, in the reader's units, without needless decimals: "32 °F", "−2.2 °C", "0 °C" */
export function temperatureText(fahrenheit: number, units: Units): string {
  const shown = units.toDisplay('degF', fahrenheit) ?? fahrenheit
  const digits = units.system === 'metric' ? 1 : 0
  const text = Number(shown.toFixed(digits)).toString().replace('-', '−')
  return `${text === '−0' ? '0' : text} ${units.label('degF')}`
}

/** A threshold's name, if it has one ("Frost"), else null */
export const thresholdName = (fahrenheit: number): string | null => FREEZE_NAMES[fahrenheit] ?? null

/** "Frost (32 °F)", or "30 °F or colder" for a threshold without a name */
export function thresholdLabel(fahrenheit: number, units: Units): string {
  const name = thresholdName(fahrenheit)
  const temperature = temperatureText(fahrenheit, units)
  return name ? `${name} (${temperature})` : `${temperature} or colder`
}

/** "frost", "hard freeze" or "freeze at 30 °F or colder", inside a sentence */
export function thresholdNoun(fahrenheit: number, units: Units): string {
  const name = thresholdName(fahrenheit)
  return name ? name.toLowerCase() : `freeze at ${temperatureText(fahrenheit, units)} or colder`
}

/** "a frost (32 °F), a hard freeze (28 °F) and a killing freeze (24 °F)"; unnamed thresholds as temperatures */
export function thresholdsInWords(thresholds: readonly number[], units: Units): string {
  const each = thresholds.map((f) => {
    const name = thresholdName(f)
    const temperature = temperatureText(f, units)
    return name ? `a ${name.toLowerCase()} (${temperature})` : temperature
  })
  return each.length > 1 ? `${each.slice(0, -1).join(', ')} and ${each.at(-1)}` : (each[0] ?? '')
}

/** "1st", "2nd", "96th" */
export function ordinal(n: number): string {
  const k = Math.round(n)
  const tens = k % 100
  const suffix = tens >= 11 && tens <= 13 ? 'th' : (['th', 'st', 'nd', 'rd'][k % 10] ?? 'th')
  return `${k}${suffix}`
}

/** Where a total ranks among the period's years, in words: the percentile's band */
export function percentileWords(percentile: number): string {
  if (percentile <= 10) return 'among the lowest of the period'
  if (percentile < 33) return 'below normal'
  if (percentile <= 67) return 'near normal'
  if (percentile < 90) return 'above normal'
  return 'among the highest of the period'
}

/** "12 days ahead of normal", "3 days behind normal", "on pace with normal" */
export function daysAheadWords(days: number): string {
  if (days === 0) return 'on pace with normal'
  const n = Math.abs(days)
  return `${plural(n, 'day')} ${days > 0 ? 'ahead of' : 'behind'} normal`
}

/** A share of years as words: 10 → "1 year in 10", 50 → "half the years", 90 → "9 years in 10" */
export function shareOfYears(percent: number): string {
  if (percent === 50) return 'half the years'
  if (percent % 10 === 0) {
    const n = percent / 10
    return `${plural(n, 'year')} in 10`
  }
  return `${Math.round(percent)}% of years`
}

/** A freeze chance as words: "a 1-in-10 chance", "no chance in the period's years", "certain in every year" */
export function chanceWords(percent: number): string {
  if (percent <= 0) return 'none of the years'
  if (percent >= 100) return 'every year'
  return `${Math.round(percent)}% of years`
}

/** A date as a reader sees it, without a year: "Apr 17" */
export const dayText = (iso: string | null | undefined): string => (iso ? formatDate(iso) : 'none')
