// The reference periods normals come from (D82): the last 30, 20, 10 or 5 whole years before this one. Normals
// default to 30 years, with 10 and 5 a switch away (Ben, 2026-11-26); 20 only for counts at points. The years are
// labelled before an answer comes (the last whole year is last year), and the answer's `meta.summary` names the
// years it found, which win where they differ (a year not yet in the archive).

export type Period = 'last30' | 'last20' | 'last10' | 'last5'

export const DEFAULT_PERIOD: Period = 'last30'

/** The quick switch: 30 years, then 10 and 5 */
export const NORMAL_PERIODS: readonly Period[] = ['last30', 'last10', 'last5']

const LENGTHS: Record<Period, number> = { last30: 30, last20: 20, last10: 10, last5: 5 }

export const periodLength = (period: Period): number => LENGTHS[period]

/** A period from a view's text (`cperiod=last10`), the default for anything else */
export function parsePeriod(text: string | null | undefined, fallback: Period = DEFAULT_PERIOD): Period {
  return text && text in LENGTHS ? (text as Period) : fallback
}

export type PeriodYears = { first: number; last: number; years: number }

/** The period's years as of `today` (ISO): the whole years before this one */
export function periodYears(period: Period, today: string): PeriodYears {
  const last = Number(today.slice(0, 4)) - 1
  const years = LENGTHS[period]
  return { first: last - years + 1, last, years }
}

/** The years an answer's `meta.summary` says it used (`first_year`, `last_year`, `years`), if it says */
export function summaryYears(summary: Record<string, unknown> | null | undefined): PeriodYears | null {
  const first = summary?.first_year
  const last = summary?.last_year
  const years = summary?.years
  if (typeof first !== 'number' || typeof last !== 'number') return null
  return { first, last, years: typeof years === 'number' ? years : last - first + 1 }
}

/** "30 years" */
export const periodName = (period: Period): string => `${LENGTHS[period]} years`

/** "30 years (1996–2025)", for a switch */
export function periodLabel(period: Period, today: string): string {
  const { first, last } = periodYears(period, today)
  return `${periodName(period)} (${first}–${last})`
}

/** "the 30 years from 1996 to 2025", for a sentence; the years an answer used where given */
export function periodWords(years: PeriodYears): string {
  return years.years === years.last - years.first + 1
    ? `the ${years.years} years from ${years.first} to ${years.last}`
    : `${years.years} years between ${years.first} and ${years.last}`
}

/** The switch's options, each labelled with its years */
export function periodOptions(today: string, periods: readonly Period[] = NORMAL_PERIODS) {
  return periods.map((value) => ({ value, label: periodLabel(value, today) }))
}
