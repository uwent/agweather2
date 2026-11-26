// The Climate tab's normals charts, over answers recorded from the dev server at Madison (2026-11-25, `units=us`,
// 1996–2025): `/weather/daily` from September 26 with `/climate/normals` for the same days, the normal high
// through the year, and the normals by month
import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'
import monthsAnswer from '@/test/fixtures/climate/months.json'
import spanAnswer from '@/test/fixtures/climate/normal-span.json'
import yearAnswer from '@/test/fixtures/climate/normal-year.json'
import recentAnswer from '@/test/fixtures/climate/recent.json'
import { testPalette as palette } from '@/test/palette'
import type { TableResponse } from '@/types/api'

import {
  departureWords,
  monthlyNormals,
  normalSpans,
  normalYear,
  normalYearOption,
  normalYearRows,
  normalYearSummary,
  recentNormal,
  recentNormalOption,
  recentNormalRows,
  recentNormalSummary,
  yearFromMonths,
} from './climateNormals'

const us = unitsFor('imperial')
const metric = unitsFor('metric')
const today = '2026-11-25'
const body = (answer: unknown) => answer as TableResponse
type Series = { id?: string; name: string; data: unknown[] }
const seriesOf = (option: object) => (option as { series: Series[] }).series

describe('normalSpans', () => {
  it('splits a span at January 1, as normals keep to one year', () => {
    expect(normalSpans('2026-09-26', '2026-12-11')).toEqual([{ start: '2026-09-26', end: '2026-12-11' }])
    expect(normalSpans('2026-11-20', '2027-01-15')).toEqual([
      { start: '2026-11-20', end: '2026-12-31' },
      { start: '2027-01-01', end: '2027-01-15' },
    ])
  })
})

describe('recentNormal', () => {
  const recent = recentNormal(body(recentAnswer), [body(spanAnswer)])

  it('puts each day’s normal beside its high and low', () => {
    expect(recent.dates[0]).toBe('2026-09-26')
    expect(recent.dates.at(-1)).toBe('2026-12-05')
    expect(recent.kinds.filter((k) => k === 'observed')).toHaveLength(60)
    expect(recent.normal.max.every((v) => v !== null)).toBe(true)
    expect(recent.years).toMatchObject({ first: 1996, last: 2025 })
  })

  it('reads a normal from either year’s answer', () => {
    const [first, second] = [structuredClone(spanAnswer), structuredClone(spanAnswer)]
    const split = 40
    for (const [name, column] of Object.entries(first.data))
      (first.data as Record<string, unknown[]>)[name] = column.slice(0, split)
    for (const [name, column] of Object.entries(second.data))
      (second.data as Record<string, unknown[]>)[name] = column.slice(split)
    const joined = recentNormal(body(recentAnswer), [body(first), body(second)])
    expect(joined.normal.min).toEqual(recent.normal.min)
  })

  it('says how far the highs and lows ran from normal, and how many days fell outside the usual range', () => {
    const summary = recentNormalSummary({ recent, units: us })
    expect(summary).toMatch(
      /^Over the last 7 days \(Nov 18 to Nov 24\), highs averaged 9 °F above normal and lows 9 °F above normal\./,
    )
    expect(summary).toContain('Over the last 30 days, highs averaged')
    expect(summary).toContain('In the forecast through Dec 5')
    expect(summary).toMatch(/Of the 60 observed days shown, \d+ had a high above its usual range/)
    expect(recentNormalSummary({ recent, units: metric })).toContain('highs averaged 5 °C above normal')
  })

  it('draws the highs and lows over their normals, in the reader’s units', () => {
    const option = recentNormalOption({ recent, units: metric, palette, today })
    const names = seriesOf(option).map((s) => s.name)
    expect(names).toEqual(expect.arrayContaining(['High', 'Low', 'Normal high (1996–2025)', 'Normal low (1996–2025)']))
    const high = seriesOf(option).find((s) => s.id === 'high')!
    expect(high.data[0]).toBeCloseTo(((recent.highs[0] as number) - 32) * (5 / 9), 2)
    const rows = recentNormalRows(recent, us)
    expect(rows.columns).toEqual(['High (°F)', 'Normal high (°F)', 'Low (°F)', 'Normal low (°F)'])
    expect(rows.rows[0].date).toBe('2026-12-05')
    expect(rows.rows[0].forecast).toBe(true)
  })

  it('names a departure in words', () => {
    expect(departureWords(4.2, us)).toBe('4 °F above normal')
    expect(departureWords(-0.3, us)).toBe('about normal')
    expect(departureWords(-3.6, metric)).toBe('2 °C below normal')
  })
})

describe('normalYear', () => {
  const normal = normalYear(body(yearAnswer), 'air_temperature_max')

  it('reads a daily normal with its usual range', () => {
    expect(normal).toMatchObject({ cumulative: false, unit: 'degF' })
    expect(normal.dates).toHaveLength(365)
    expect(normalYearSummary({ normal, units: us, today, label: 'Average high' })).toMatch(
      /^Average high: the normal over the 30 years from 1996 to 2025\. On Nov 25, the normal is 41 °F, and between 29 °F and 55 °F in 8 years out of 10\. It is highest around /,
    )
  })

  it('takes a total’s running total from January 1', () => {
    const answer = structuredClone(yearAnswer) as unknown as TableResponse
    const data = answer.data as Record<string, unknown[]>
    data.precipitation_sum_cum = data.air_temperature_max.map((_, i) => i * 0.1)
    data.precipitation_sum_cum_p10 = data.air_temperature_max.map((_, i) => i * 0.05)
    data.precipitation_sum_cum_p90 = data.air_temperature_max.map((_, i) => i * 0.15)
    answer.meta.units.precipitation_sum_cum = 'in'
    const total = normalYear(answer, 'precipitation_sum')
    expect(total).toMatchObject({ cumulative: true, unit: 'in' })
    expect(normalYearSummary({ normal: total, units: us, today, label: 'Precipitation' })).toContain(
      'The normal total from January 1 to Nov 25 is 32.80 in, and between 16.40 in and 49.20 in in 8 years out of 10.',
    )
    const option = normalYearOption({
      normal: total,
      units: metric,
      palette,
      today,
      label: 'Precipitation',
      color: 'blue',
    })
    const line = seriesOf(option).at(-1)!
    expect(line.data[10]).toBeCloseTo(25.4, 3)
  })

  it('tables the normal by date', () => {
    const rows = normalYearRows(normal, us)
    expect(rows.columns).toEqual(['Normal (°F)', '10th percentile', '90th percentile'])
    expect(rows.rows[328]).toMatchObject({ date: '2026-11-25', values: ['41', '29', '55'] })
  })
})

describe('monthlyNormals', () => {
  it('reads the normals by month with their units, and a year from them', () => {
    const table = monthlyNormals(body(monthsAnswer))
    expect(table.months).toHaveLength(12)
    expect(table.units).toMatchObject({
      air_temperature_max: 'degF',
      precipitation_sum: 'in',
      shortwave_radiation_sum: 'MJ_m2',
    })
    expect(yearFromMonths(table.months, table.values.precipitation_sum, true)).toBeCloseTo(38.8529, 3)
    // Temperatures: the months' means weighted by their days
    expect(yearFromMonths(['2026-01', '2026-02'], [31, 59], false)).toBeCloseTo((31 * 31 + 59 * 28) / 59, 6)
    expect(yearFromMonths(['2026-01', '2026-02'], [31, null], false)).toBeNull()
  })
})
