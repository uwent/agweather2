import { describe, expect, it } from 'vitest'

import { calendarRows, dateOfDay, dayOfYear, daysInYear, isLeapYear, leapNote, longDate } from './calendar'

describe('the day-of-year calendar', () => {
  it('knows leap years, centuries included', () => {
    expect([1900, 2000, 2024, 2026, 2100].map(isLeapYear)).toEqual([false, true, true, false, false])
    expect(daysInYear(2028)).toBe(366)
  })

  it('converts a date to its day of the year and back', () => {
    expect(dayOfYear('2026-01-01')).toBe(1)
    expect(dayOfYear('2026-03-01')).toBe(60)
    expect(dayOfYear('2028-03-01')).toBe(61)
    expect(dayOfYear('2100-12-31')).toBe(365)
    expect(dayOfYear('1900-12-31')).toBe(365)
    expect(dateOfDay(2026, 60)).toBe('2026-03-01')
    expect(dateOfDay(2000, 366)).toBe('2000-12-31')
    expect(dateOfDay(1900, 1)).toBe('1900-01-01')
    expect(dateOfDay(2026, 366)).toBeNull()
    expect(dateOfDay(2026, 0)).toBeNull()
    expect(dateOfDay(2026, 1.5)).toBeNull()
  })

  it('lays a year out as 31 rows of 12 months, blank past each month’s end', () => {
    const rows = calendarRows(2026)
    expect(rows).toHaveLength(31)
    expect(rows[0]).toEqual([1, 32, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335])
    expect(rows[28][1]).toBeNull()
    expect(calendarRows(2028)[28][1]).toBe(60)
    expect(rows[30]).toEqual([31, null, 90, null, 151, null, 212, 243, null, 304, null, 365])
  })

  it('says whether one is a leap year', () => {
    expect(leapNote(2028)).toMatch(/^2028 is a leap year, with 366 days/)
    expect(leapNote(2026)).toMatch(/^2026 is not a leap year/)
    expect(longDate('2027-04-01')).toBe('April 1, 2027')
  })
})
