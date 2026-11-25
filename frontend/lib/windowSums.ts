// Sums of a daily value over the days ending on each row (NEWA's 2-, 7- and 14-day columns), computed in the
// browser from a model run's rows so the table needs no other request. A sum covers the rows the run has: before
// its first row (the biofix) nothing has accumulated, so an early window is shorter, not missing. A missing day adds
// nothing and is counted (D45: a total reports how many days it lacks); an estimated day adds its estimate and is
// counted too, so the table can say "includes N estimated days". A window with no known day has no sum.

import type { Day } from './tableRows'

export type WindowSum = {
  /** The sum of the known days, null when none is known */
  value: number | null
  /** Rows the window covers (fewer than its length near the run's start) */
  days: number
  /** Of those, days without a value */
  missing: number
  /** Of those, days whose value is an estimate */
  estimated: number
}

/** For each row, the sum of `column` over the `length` rows ending on it */
export function windowSums(days: readonly Day[], column: string, length: number): WindowSum[] {
  if (!Number.isInteger(length) || length < 1) throw new Error(`a window is a whole number of days, not ${length}`)
  return days.map((_, end) => {
    let value = 0
    let known = 0
    let missing = 0
    let estimated = 0
    const start = Math.max(0, end - length + 1)
    for (let k = start; k <= end; k++) {
      const day = days[k]
      const amount = day.values[column]
      if (amount === null || amount === undefined || Number.isNaN(amount)) {
        missing += 1
        continue
      }
      value += amount
      known += 1
      if (day.estimated.has(column)) estimated += 1
    }
    return { value: known ? Number(value.toFixed(6)) : null, days: end - start + 1, missing, estimated }
  })
}

/** The 2-, 7- and 14-day sums NEWA's tables show, by length */
export const WINDOWS = [2, 7, 14] as const

export function allWindowSums(days: readonly Day[], column: string): Record<(typeof WINDOWS)[number], WindowSum[]> {
  return {
    2: windowSums(days, column, 2),
    7: windowSums(days, column, 7),
    14: windowSums(days, column, 14),
  }
}
