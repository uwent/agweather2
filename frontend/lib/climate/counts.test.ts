// Counts of days against normal, over answers recorded from the dev server at Madison (2026-11-25, `units=us`,
// 1996–2025): `/climate/compare` for November 2026 and `/climate/normals` by month, with the nine counts
import { describe, expect, it } from 'vitest'

import { compareTable } from '@/lib/charts/climateCharts'
import { units as unitsFor } from '@/lib/units'
import countsAnswer from '@/test/fixtures/climate/counts.json'
import monthsAnswer from '@/test/fixtures/climate/counts-months.json'
import type { TableResponse } from '@/types/api'

import {
  countColumn,
  countLabel,
  countMonths,
  countRows,
  countSpec,
  countWords,
  DAY_COUNTS,
  type DayCount,
} from './counts'

const us = unitsFor('imperial')
const metric = unitsFor('metric')
const count = (variable: DayCount['variable'], bound: DayCount['bound'], value: number) =>
  DAY_COUNTS.find((c) => c.variable === variable && c.bound === bound && c.value === value)!

describe('the counts', () => {
  it('asks as `/climate/compare` takes them and reads the columns it names back', () => {
    // The API echoes a decimal as it names columns (`0p01`)
    expect(DAY_COUNTS.map((c) => countSpec(c).replace('.', 'p'))).toEqual(countsAnswer.meta.request.count)
    const dry = count('precipitation_sum', 'below', 0.01)
    expect(countSpec(dry)).toBe('precipitation_sum:days_below_0.01')
    expect(countColumn(dry)).toBe('precipitation_sum_days_below_0p01')
    expect(Object.keys(countsAnswer.data)).toContain(`${countColumn(dry)}_cum`)
  })

  it('names each count with its threshold in the reader’s units', () => {
    expect(countLabel(count('air_temperature_max', 'above', 90), us)).toBe('Highs of 90 °F or more')
    expect(countLabel(count('air_temperature_max', 'above', 90), metric)).toBe('Highs of 32.2 °C or more')
    expect(countLabel(count('air_temperature_max', 'below', 32), us)).toBe('Days that stay at or below 32 °F')
    expect(countLabel(count('air_temperature_min', 'below', 28), us)).toBe('Lows of 28 °F or less')
    expect(countLabel(count('air_temperature_min', 'above', 70), us)).toBe('Warm nights (lows of 70 °F or more)')
    expect(countLabel(count('precipitation_sum', 'below', 0.01), us)).toBe(
      'Dry days (0.01 in of precipitation or less)',
    )
    expect(countLabel(count('precipitation_sum', 'above', 0.5), us)).toBe('Days with 0.5 in of precipitation or more')
    expect(countLabel(count('precipitation_sum', 'above', 1), metric)).toBe(
      'Days with 25.4 mm of precipitation or more',
    )
  })

  it('puts a percentile in words', () => {
    expect(countWords(3)).toBe('Among the fewest')
    expect(countWords(50)).toBe('Near normal')
    expect(countWords(68)).toBe('More than usual')
    expect(countWords(95)).toBe('Among the most')
    expect(countWords(null)).toBe('—')
  })
})

describe('countRows', () => {
  it('reads each count as of the last observed day', () => {
    const rows = countRows(compareTable(countsAnswer as unknown as TableResponse))
    const freezes = rows.find((r) => r.count === count('air_temperature_min', 'below', 32))!
    expect(freezes).toMatchObject({ now: 3, normal: 10.4, low: 4, high: 14.4, lastYear: 4, percentile: 3 })
    const dry = rows.find((r) => r.count === count('precipitation_sum', 'below', 0.01))!
    expect(dry).toMatchObject({ now: 19, normal: 16.9, percentile: 68, missingDays: 0 })
  })

  it('has nothing to show before the month’s first observed day', () => {
    const table = compareTable(countsAnswer as unknown as TableResponse)
    const rows = countRows({ ...table, asOf: '2026-10-31' })
    expect(rows.every((r) => r.now === null && r.normal === null && r.percentile === null)).toBe(true)
  })
})

describe('countMonths', () => {
  it('gives each count’s normal by month', () => {
    const months = countMonths(monthsAnswer as unknown as TableResponse)
    expect(months.months).toHaveLength(12)
    expect(months.values[countColumn(count('air_temperature_max', 'above', 86))]?.[6]).toBe(3.5)
  })
})
