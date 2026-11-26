import { describe, expect, it } from 'vitest'

import risk from '@/test/fixtures/site/risk.json'

import { coordinates, dayBasisWords, placeName, rangeDays, riskRows, sourceWords } from './text'

describe('site text', () => {
  it('names the place and the point', () => {
    expect(placeName({ county: 'Dane County', state: 'WI' })).toBe('Dane County, WI')
    expect(placeName({ county: null, state: 'ON' })).toBe('ON')
    expect(placeName(null)).toBeNull()
    expect(coordinates(43.0731, -89.40123)).toBe('43.0731° N, 89.4012° W')
    expect(coordinates(-33.9, 151.2)).toBe('33.9° S, 151.2° E')
  })

  it('says whose days a site uses and where its weather comes from', () => {
    expect(dayBasisWords({ in_box: true, timezone: 'America/Chicago' })).toBe(
      'Days run midnight to midnight Central Standard Time all year, as on our maps.',
    )
    expect(dayBasisWords({ in_box: false, timezone: 'America/New_York' })).toContain(
      "this location's own clock (America/New York)",
    )
    expect(sourceWords({ in_box: false })).toContain('Open-Meteo')
    expect(sourceWords({ in_box: true })).toContain('NOAA')
  })

  it("reads /risk's columns, highest risk first", () => {
    const rows = riskRows(risk)
    expect(rows[0]).toMatchObject({ model: 'potato-volunteer', label: 'Very high', level: 3, missingDays: 0 })
    expect(rows.at(-1)!.level).toBeNull()
    expect(rows).toHaveLength(risk.data.model.length)
  })

  it('gives the days a range asks for', () => {
    expect(rangeDays('week', '2026-11-25', null)).toEqual({ start: '2026-11-18', end: null })
    expect(rangeDays('month', '2026-11-25', null)).toEqual({ start: '2026-10-26', end: null })
    expect(rangeDays('season', '2026-11-25', null)).toEqual({ start: '2026-01-01', end: null })
    const custom = { start: '2026-06-01', end: '2026-06-30' }
    expect(rangeDays('custom', '2026-11-25', custom)).toEqual(custom)
    expect(rangeDays('custom', '2026-11-25', null).start).toBe('2026-10-26')
  })
})
