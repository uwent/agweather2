import { describe, expect, it } from 'vitest'

import { addDays, daysBetween, formatDate, relativeDay } from './dates'

describe('dates', () => {
  it('adds days across months and leap days, as calendar dates', () => {
    expect(addDays('2026-06-30', 1)).toBe('2026-07-01')
    expect(addDays('2028-02-28', 1)).toBe('2028-02-29')
    expect(addDays('2026-03-08', 1)).toBe('2026-03-09') // daylight saving starts in the US
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31')
  })

  it('counts days between dates', () => {
    expect(daysBetween('2026-07-01', '2026-07-31')).toBe(30)
    expect(daysBetween('2026-11-01', '2026-11-02')).toBe(1) // daylight saving ends
  })

  it('formats without shifting the day in the browser time zone', () => {
    expect(formatDate('2026-07-01')).toBe('Jul 1')
    expect(formatDate('2026-07-01', { year: true })).toBe('Jul 1, 2026')
    expect(formatDate('2026-07-01', { weekday: true })).toBe('Wed, Jul 1')
    expect(formatDate(null)).toBe('—')
  })

  it('says how long ago a day was', () => {
    expect(relativeDay('2026-07-10', '2026-07-10')).toBe('today')
    expect(relativeDay('2026-07-09', '2026-07-10')).toBe('yesterday')
    expect(relativeDay('2026-07-07', '2026-07-10')).toBe('3 days ago')
    expect(relativeDay('2026-07-11', '2026-07-10')).toBe('tomorrow')
    expect(relativeDay('2026-07-13', '2026-07-10')).toBe('in 3 days')
  })
})
