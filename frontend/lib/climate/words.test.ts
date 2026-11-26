import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'

import { parsePeriod, periodLabel, periodOptions, periodWords, periodYears, summaryYears } from './periods'
import {
  daysAheadWords,
  ordinal,
  percentileWords,
  shareOfYears,
  temperatureText,
  thresholdLabel,
  thresholdNoun,
  thresholdsInWords,
} from './words'

const us = unitsFor('imperial')
const metric = unitsFor('metric')

describe('words', () => {
  it('names the freeze thresholds, in the reader’s units', () => {
    expect(thresholdLabel(32, us)).toBe('Frost (32 °F)')
    expect(thresholdLabel(28, metric)).toBe('Hard freeze (−2.2 °C)')
    expect(thresholdLabel(32, metric)).toBe('Frost (0 °C)')
    expect(thresholdLabel(30, us)).toBe('30 °F or colder')
    expect(thresholdNoun(24, us)).toBe('killing freeze')
    expect(thresholdNoun(26, us)).toBe('freeze at 26 °F or colder')
    expect(temperatureText(24, metric)).toBe('−4.4 °C')
    expect(thresholdsInWords([32, 28, 24], us)).toBe(
      'a frost (32 °F), a hard freeze (28 °F) and a killing freeze (24 °F)',
    )
    expect(thresholdsInWords([32, 26], us)).toBe('a frost (32 °F) and 26 °F')
  })

  it('ranks, compares and shares in words', () => {
    expect([1, 2, 3, 4, 11, 12, 13, 21, 62, 96, 100].map(ordinal)).toEqual([
      '1st',
      '2nd',
      '3rd',
      '4th',
      '11th',
      '12th',
      '13th',
      '21st',
      '62nd',
      '96th',
      '100th',
    ])
    expect([5, 20, 50, 80, 95].map(percentileWords)).toEqual([
      'among the lowest of the period',
      'below normal',
      'near normal',
      'above normal',
      'among the highest of the period',
    ])
    expect([12, 1, 0, -3].map(daysAheadWords)).toEqual([
      '12 days ahead of normal',
      '1 day ahead of normal',
      'on pace with normal',
      '3 days behind normal',
    ])
    expect([10, 50, 90, 25].map(shareOfYears)).toEqual([
      '1 year in 10',
      'half the years',
      '9 years in 10',
      '25% of years',
    ])
  })
})

describe('periods', () => {
  it('labels the whole years before this one', () => {
    expect(periodYears('last30', '2026-11-25')).toEqual({ first: 1996, last: 2025, years: 30 })
    expect(periodLabel('last5', '2026-01-02')).toBe('5 years (2021–2025)')
    expect(periodOptions('2026-11-25').map((o) => o.value)).toEqual(['last30', 'last10', 'last5'])
    expect(periodWords({ first: 1996, last: 2025, years: 30 })).toBe('the 30 years from 1996 to 2025')
    expect(periodWords({ first: 1996, last: 2025, years: 29 })).toBe('29 years between 1996 and 2025')
  })

  it('reads a period from a view and an answer’s years', () => {
    expect(parsePeriod('last10')).toBe('last10')
    expect(parsePeriod('last7')).toBe('last30')
    expect(parsePeriod(null)).toBe('last30')
    expect(summaryYears({ first_year: 2016, last_year: 2025, years: 10 })).toEqual({
      first: 2016,
      last: 2025,
      years: 10,
    })
    expect(summaryYears({})).toBeNull()
  })
})
