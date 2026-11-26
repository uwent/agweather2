import { describe, expect, it } from 'vitest'

import { freezeChances, freezeDates, yearFreezes } from '@/lib/charts/climateCharts'
import { units } from '@/lib/units'
import chancesBody from '@/test/fixtures/climate/chances.json'
import freezeBody from '@/test/fixtures/climate/freeze.json'
import frostBody from '@/test/fixtures/climate/frost.json'
import presets from '@/test/fixtures/site/presets.json'
import type { TableResponse } from '@/types/api'

import {
  coldestLow,
  cropFreezes,
  daysFromTypical,
  freezeAnswer,
  freezeMapUrl,
  freezeNoun,
  fromOpenMeteo,
  lookUp,
  lookUpWords,
  mapThreshold,
  seasonLength,
  stageOf,
  thresholdsFor,
  toolRows,
} from './freeze'

const us = units('imperial')
const metric = units('metric')
const dates = freezeDates(frostBody as unknown as TableResponse)
const chances = freezeChances(chancesBody as unknown as TableResponse)
const own = yearFreezes(freezeBody as unknown as TableResponse)
const frostRow = dates.rows[0]

describe('thresholds', () => {
  it('takes 32, 28 and 24 °F, a crop’s killing freeze or the reader’s own', () => {
    const crops = cropFreezes(presets.data)
    expect(crops.map((c) => c.id)).toContain('alfalfa')
    const alfalfa = crops.find((c) => c.id === 'alfalfa')!
    expect(alfalfa.fahrenheit).toBe(24)
    expect(thresholdsFor({ choice: 'standard', crop: null, custom: null })).toEqual([32, 28, 24])
    expect(thresholdsFor({ choice: 'crop', crop: alfalfa, custom: null })).toEqual([24])
    expect(thresholdsFor({ choice: 'crop', crop: null, custom: null })).toBeNull()
    expect(thresholdsFor({ choice: 'custom', crop: null, custom: 30.04 })).toEqual([30])
    expect(thresholdsFor({ choice: 'custom', crop: null, custom: 60 })).toBeNull()
  })

  it('names a threshold, or says its temperature', () => {
    expect(freezeNoun(32, us)).toBe('frost (32 °F)')
    expect(freezeNoun(30, us)).toBe('freeze at 30 °F or colder')
    expect(freezeNoun(28, metric)).toBe('hard freeze (−2.2 °C)')
  })
})

describe('a year’s dates', () => {
  it('knows where a year stands', () => {
    expect(stageOf(2025, '2026-11-25')).toBe('past')
    expect(stageOf(2026, '2026-06-30')).toBe('spring')
    expect(stageOf(2026, '2026-07-01')).toBe('fall')
  })

  it('counts the season without a freeze, so far in fall, not before July', () => {
    expect(seasonLength({ spring: '2026-04-07', fall: '2026-11-14' }, 2026, '2026-11-25')).toEqual({
      days: 221,
      soFar: false,
    })
    expect(seasonLength({ spring: '2026-04-07', fall: null }, 2026, '2026-09-01')).toEqual({ days: 147, soFar: true })
    expect(seasonLength({ spring: '2026-04-07', fall: null }, 2026, '2026-05-01')).toBeNull()
    // A past year without a fall freeze runs to the year's end
    expect(seasonLength({ spring: null, fall: null }, 2024, '2026-11-25')).toEqual({ days: 366, soFar: false })
  })

  it('finds the forecast’s coldest low from today on', () => {
    const daily = {
      meta: {},
      data: {
        date: ['2026-11-24', '2026-11-25', '2026-11-26', '2026-11-27'],
        air_temperature_min: [20, 28.9, 37, null],
      },
    } as unknown as TableResponse
    expect(coldestLow(daily, '2026-11-25')).toEqual({ date: '2026-11-25', fahrenheit: 28.9 })
    expect(coldestLow(null, '2026-11-25')).toBeNull()
  })

  it('says when dates come from Open-Meteo', () => {
    expect(fromOpenMeteo(freezeBody as unknown as TableResponse)).toBe(false)
    expect(fromOpenMeteo({ meta: { sources: ['openmeteo'] }, data: {} } as unknown as TableResponse)).toBe(true)
  })
})

describe('the answer', () => {
  const answer = (overrides: Partial<Parameters<typeof freezeAnswer>[0]>) =>
    freezeAnswer({
      fahrenheit: 32,
      own: own.get(32)!,
      typical: frostRow,
      year: 2026,
      today: '2026-11-25',
      units: us,
      coldest: null,
      ...overrides,
    })

  it('puts this fall’s first freeze against the typical date', () => {
    expect(daysFromTypical('2026-11-14', '2026-10-21')).toBe(24)
    expect(answer({})).toBe(
      'This fall’s first frost (32 °F) came on November 14, 24 days later than typical (October 21).',
    )
    expect(answer({ today: '2026-11-10' })).toBe(
      'This fall’s first frost (32 °F) is forecast for November 14, 24 days later than typical (October 21).',
    )
  })

  it('says none yet, with the typical date and the forecast’s coldest low', () => {
    expect(
      answer({
        own: { spring: '2026-04-07', fall: null },
        today: '2026-10-01',
        coldest: { date: '2026-10-05', fahrenheit: 35 },
      }),
    ).toBe(
      'There has been no frost (32 °F) yet this fall. In half the years the first came by October 21. The coldest low in the forecast is 35 °F, on Mon, Oct 5.',
    )
    expect(answer({ own: { spring: '2026-04-07', fall: null }, today: '2026-10-22' })).toBe(
      'There has been no frost (32 °F) yet this fall. In half the years the first came by October 21, 1 day ago.',
    )
    expect(answer({ own: { spring: '2026-04-07', fall: null }, today: '2026-11-05' })).toBe(
      'There has been no frost (32 °F) yet this fall. In half the years the first came by October 21, 15 days ago.',
    )
    expect(answer({ own: { spring: '2026-04-07', fall: null }, typical: null })).toBe(
      'There has been no frost (32 °F) yet this fall.',
    )
  })

  it('gives this spring’s latest freeze so far', () => {
    expect(answer({ own: { spring: '2026-04-07', fall: null }, today: '2026-05-01' })).toBe(
      'This spring’s latest frost (32 °F) so far came on April 7. In half the years the last came by April 17, and in 1 year in 10 after May 3.',
    )
  })

  it('gives a past year’s both', () => {
    expect(answer({ own: { spring: '2010-04-09', fall: '2010-10-29' }, year: 2010 })).toBe(
      'In 2010, the last frost (32 °F) of spring came on April 9, 8 days earlier than typical (April 17), and the first of fall came on October 29, 8 days later than typical (October 21).',
    )
  })
})

describe('the rows and a date looked up', () => {
  it('puts the year’s dates beside the period’s, threshold by threshold', () => {
    const rows = toolRows({ thresholds: [32, 28, 24], own, dates, year: 2026, today: '2026-11-25' })
    expect(rows.map((r) => r.typical?.lastSpring[50])).toEqual(['2026-04-17', '2026-04-08', '2026-03-29'])
    expect(rows[0].season).toEqual({ days: 221, soFar: false })
    // Before the period's dates come
    expect(toolRows({ thresholds: [32], own, dates: null, year: 2026, today: '2026-11-25' })[0].typical).toBeNull()
  })

  it('gives the chance after a spring date and by a fall date', () => {
    const spring = lookUp(chances, '2019-05-01')!
    expect(spring.season).toBe('spring')
    expect(spring.date).toBe('2026-05-01')
    const frost = spring.chances.find((c) => c.fahrenheit === 32)!
    expect(lookUpWords(frost, spring.date, spring.season, us)).toMatch(
      /^A frost \(32 °F\) came after May 1 in \d+% of years\.$/,
    )
    const fall = lookUp(chances, '2026-12-31')!
    expect(fall.season).toBe('fall')
    expect(lookUpWords({ fahrenheit: 32, chance: 100 }, fall.date, fall.season, us)).toBe(
      'Every year had had its first frost (32 °F) by December 31.',
    )
    expect(lookUpWords({ fahrenheit: 24, chance: 0 }, '2026-06-30', 'spring', us)).toBe(
      'No year had a killing freeze (24 °F) after June 30.',
    )
    // February 29 reads as February 28 in a year without it
    expect(lookUp(chances, '2024-02-29')?.date).toBe('2026-02-28')
  })
})

describe('the map', () => {
  it('links the freeze layers at the nearest threshold the map holds', () => {
    expect(mapThreshold(29)).toBe(28)
    expect(mapThreshold(30)).toBe(32) // a tie goes to the warmer
    expect(mapThreshold(25)).toBe(24)
    expect(mapThreshold(40)).toBe(32)
    expect(
      freezeMapUrl({
        layer: 'freeze_dates',
        fahrenheit: 32,
        period: 'last30',
        season: 'fall',
        at: { lat: 43.07311, lng: -89.4 },
      }),
    ).toBe('/map?layer=freeze_dates&output=first_fall_p50&threshold=32&at=43.0731,-89.4')
    expect(
      freezeMapUrl({
        layer: 'freeze_chance',
        fahrenheit: 28,
        period: 'last10',
        season: 'spring',
        date: '2026-05-01',
        at: null,
      }),
    ).toBe('/map?layer=freeze_chance&date=2026-05-01&threshold=28&period=last10')
  })
})
