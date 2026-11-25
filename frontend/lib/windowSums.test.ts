import { describe, expect, it } from 'vitest'

import type { Day } from './tableRows'
import { allWindowSums, windowSums } from './windowSums'

const day = (date: string, value: number | null, estimated = false): Day => ({
  date,
  kind: 'observed',
  values: { dsv: value },
  estimated: new Set(estimated ? ['dsv'] : []),
  missing: new Set(value === null ? ['dsv'] : []),
})

const days = [
  day('2026-07-01', 1),
  day('2026-07-02', 3),
  day('2026-07-03', null),
  day('2026-07-04', 2, true),
  day('2026-07-05', 0),
]

describe('windowSums', () => {
  it('sums the days ending on each row, shorter near the start', () => {
    expect(windowSums(days, 'dsv', 2).map((s) => s.value)).toEqual([1, 4, 3, 2, 2])
    expect(windowSums(days, 'dsv', 2).map((s) => s.days)).toEqual([1, 2, 2, 2, 2])
  })

  it('counts missing days without adding them, and estimated days as they are added', () => {
    const week = windowSums(days, 'dsv', 7)
    expect(week.at(-1)).toEqual({ value: 6, days: 5, missing: 1, estimated: 1 })
    expect(week[2]).toEqual({ value: 4, days: 3, missing: 1, estimated: 0 })
  })

  it('has no sum where no day in the window is known', () => {
    expect(windowSums([day('2026-07-01', null), day('2026-07-02', null)], 'dsv', 2).map((s) => s.value)).toEqual([
      null,
      null,
    ])
  })

  it("has no sum for a column the rows don't have", () => {
    expect(windowSums(days, 'dd', 7).every((s) => s.value === null && s.missing === s.days)).toBe(true)
  })

  it('takes whole days only', () => {
    expect(() => windowSums(days, 'dsv', 0)).toThrow()
    expect(() => windowSums(days, 'dsv', 1.5)).toThrow()
  })

  it("gives NEWA's 2-, 7- and 14-day sums together", () => {
    const sums = allWindowSums(days, 'dsv')
    expect(Object.keys(sums)).toEqual(['2', '7', '14'])
    expect(sums[14].at(-1)!.value).toBe(6)
  })
})
