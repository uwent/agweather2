import { describe, expect, it } from 'vitest'

import { dataThrough, formatHour, timeWords } from './words'

describe('time in words', () => {
  it('gives hours in Central Standard Time all year', () => {
    expect(formatHour('2026-11-25T20')).toBe('2 p.m. CST, Nov 25, 2026')
    expect(formatHour('2026-07-08T05:00Z')).toBe('11 p.m. CST, Jul 7, 2026')
    expect(formatHour('2026-07-08T06', false)).toBe('midnight CST')
    expect(formatHour('2026-07-08T18', false)).toBe('noon CST')
  })

  it('says how new the data is', () => {
    const range = { first: '2016-01-01', last: '2026-11-24', forecast_through: '2026-12-06' }
    expect(dataThrough({ range, time_axis: 'day' })).toBe('Observed through Nov 24, 2026 · forecast to Dec 6, 2026')
    expect(dataThrough({ range: { ...range, forecast_through: null }, time_axis: 'day' })).toBe(
      'Observed through Nov 24, 2026',
    )
    expect(dataThrough({ range: { first: null, last: null, forecast_through: null }, time_axis: 'none' })).toBeNull()
  })

  it('names a map’s day or range', () => {
    expect(timeWords('latest', null, '2026-11-24', false)).toBe('Nov 24, 2026')
    expect(timeWords('2026-07-01..2026-07-14', 'sum', null, false)).toBe('Jul 1 to Jul 14, 2026 (total)')
    expect(timeWords('2025-11-01..2026-02-01', 'mean', null, false)).toBe('Nov 1, 2025 to Feb 1, 2026 (average)')
    expect(timeWords('2026-07-08T15', null, null, true)).toBe('9 a.m. CST, Jul 8, 2026')
  })
})
