// Climate's chart builders, over answers recorded from the dev server at Madison (frontend/test/fixtures/climate,
// 2026-11-25: `/climate/compare` with modified 50/86 degree days and precipitation, `/climate/frost`,
// `/climate/frost/chances`, all `units=us` over the 30 years 1996–2025)
import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'
import chancesAnswer from '@/test/fixtures/climate/chances.json'
import compareAnswer from '@/test/fixtures/climate/compare.json'
import frostAnswer from '@/test/fixtures/climate/frost.json'
import { testPalette as palette } from '@/test/palette'
import type { TableResponse } from '@/types/api'

import {
  compareOption,
  compareRows,
  compareSummary,
  compareTable,
  freezeChances,
  freezeDates,
  freezeOddsOption,
  freezeOddsRows,
  freezeSummary,
  measureColor,
  normalBand,
} from './climateCharts'

const us = unitsFor('imperial')
const metric = unitsFor('metric')
const today = '2026-11-25'
const DD = 'dd_modified_50_86'

type Series = { id?: string; name: string; data: unknown[]; lineStyle?: { type?: string; color?: string } }
const seriesOf = (option: object) => (option as { series: Series[] }).series
const byId = (option: object, id: string) => seriesOf(option).find((s) => s.id === id)!

describe('normalBand', () => {
  it('draws the spread as a faint band under the dashed normal', () => {
    const series = normalBand({
      id: 'n',
      dates: ['2026-01-01', '2026-01-02', '2026-01-03'],
      mean: [1, 2, null],
      low: [0.5, 1.5, null],
      high: [2, 3, null],
      color: 'normal',
      name: 'Normal',
    }) as Series[]
    expect(series.map((s) => s.name)).toEqual(['n lower', 'Normal, usual range', 'Normal'])
    expect(series[0].data).toEqual([0.5, 1.5, null])
    expect(series[1].data).toEqual([1.5, 1.5, null]) // stacked: the band's height above its lower edge
    expect(series[2].data).toEqual([1, 2, null])
    expect(series[2].lineStyle).toMatchObject({ type: 'dashed', color: 'normal' })
  })

  it('fits short columns to the dates and passes the axes on', () => {
    const series = normalBand({
      id: 'n',
      dates: ['a', 'b'],
      mean: [1],
      low: [],
      high: [],
      color: 'c',
      name: 'N',
      xAxisIndex: 1,
      yAxisIndex: 1,
    }) as (Series & { xAxisIndex: number })[]
    expect(series[2].data).toEqual([1, null])
    expect(series.every((s) => s.xAxisIndex === 1)).toBe(true)
  })
})

describe('the comparison with normal', () => {
  const table = compareTable(compareAnswer as unknown as TableResponse)

  it('keeps every day of the year, with no kind past the forecast', () => {
    expect(table.dates).toHaveLength(365)
    expect(table.kinds.at(-1)).toBeNull()
    expect(table.values[`${DD}_cum_normal`].at(-1)).not.toBeNull() // the normal runs to December 31
    expect(table.asOf).toBe('2026-11-24')
    expect(table.totals[DD]).toEqual({ percentile: 96, days_ahead: null })
    expect(table.years).toEqual({ first: 1996, last: 2025, years: 30 })
    expect(table.units[`${DD}_cum`]).toBe('degF_day')
    expect(table.units.precipitation_sum_cum).toBe('in')
  })

  it('draws this year over the normal and its band, last year and the forecast', () => {
    const option = compareOption({ table, column: DD, units: us, palette, today, label: 'Degree days' })
    const names = seriesOf(option).map((s) => s.name)
    expect(names).toEqual(
      expect.arrayContaining(['2026', '2025', 'Normal (1996–2025)', 'Normal (1996–2025), usual range']),
    )
    const now = byId(option, 'this-year')
    expect(now.lineStyle?.color).toBe(measureColor(DD, palette))
    const k = table.dates.indexOf('2026-11-24')
    expect(now.data[k]).toBe(3323.4)
    expect(now.data.at(-1)).toBeNull() // nothing past the forecast
    expect(byId(option, 'normal-mean').data[k]).toBe(2902.7)
    // The forecast's shading stops where the forecast does
    const shading = byId(option, 'shading-0').data
    expect(shading[k]).toBeNull()
    expect(shading[k + 2]).toBe(1)
    expect(shading.at(-1)).toBeNull()
    const legend = (option as { legend: { data: string[] } }).legend.data
    expect(legend).not.toContain('normal lower')
    expect((option as { yAxis: { name: string }[] }).yAxis[0].name).toBe('Degree days (°F·d)')
  })

  it('leaves last year out when asked', () => {
    const option = compareOption({ table, column: DD, units: us, palette, today, label: 'DD', lastYear: false })
    expect(seriesOf(option).some((s) => s.id === 'last-year')).toBe(false)
  })

  it('converts to the reader’s units at display', () => {
    const option = compareOption({ table, column: 'precipitation_sum', units: metric, palette, today, label: 'Rain' })
    const k = table.dates.indexOf('2026-11-24')
    expect(byId(option, 'this-year').data[k]).toBeCloseTo(37.4252 * 25.4, 2)
    expect((option as { yAxis: { name: string }[] }).yAxis[0].name).toBe('Rain (mm)')
  })

  it('says it in words: the total, the departure, the rank, the usual range and last year', () => {
    expect(compareSummary({ table, column: DD, units: us, label: 'Degree days' })).toBe(
      'Degree days from Jan 1 through Nov 24: 3,323 °F·d. That is 421 °F·d more than the normal of 2,903 °F·d for the date. It ranks in the 96th percentile of the 30 years from 1996 to 2025: among the highest of the period. In 8 years out of 10, the total by this date was between 2,521 °F·d and 3,244 °F·d. The normal doesn’t reach this total until after the end of the year. Last year by the same date: 3,054 °F·d.',
    )
    expect(compareSummary({ table, column: 'precipitation_sum', units: us, label: 'Precipitation' })).toContain(
      'Precipitation from Jan 1 through Nov 24: 37.43 in. That is 0.90 in more than the normal of 36.52 in for the date. It ranks in the 62nd percentile',
    )
  })

  it('says days ahead of normal, and when nothing is observed yet', () => {
    const ahead = { ...table, totals: { [DD]: { percentile: 70, days_ahead: 12 } } }
    expect(compareSummary({ table: ahead, column: DD, units: us, label: 'Degree days' })).toContain(
      'This year is 12 days ahead of normal.',
    )
    const none = { ...table, asOf: null }
    expect(compareSummary({ table: none, column: DD, units: us, label: 'Degree days' })).toBe(
      'No days from Jan 1 have been observed yet. Over the 30 years from 1996 to 2025, the normal total by Dec 31 is 2,909 °F·d.',
    )
  })

  it('tables the days newest first', () => {
    const rows = compareRows(table, DD, us)
    expect(rows.columns).toEqual(['2026 (°F·d)', 'Normal (°F·d)', '10th percentile', '90th percentile', '2025 (°F·d)'])
    expect(rows.rows[0].date).toBe('2026-12-31')
    expect(rows.rows.find((r) => r.date === '2026-11-24')!.values[0]).toBe('3323')
  })
})

describe('freeze odds', () => {
  const chances = freezeChances(chancesAnswer as unknown as TableResponse)
  const dates = freezeDates(frostAnswer as unknown as TableResponse)

  it('reads the long table by threshold', () => {
    expect(chances.thresholds).toEqual([32, 28, 24])
    expect(chances.dates).toHaveLength(365)
    expect(chances.unit).toBe('degF')
    expect(chances.season[0]).toBe('spring')
    expect(chances.season.at(-1)).toBe('fall')
    expect(chances.chance['32'][chances.dates.indexOf('2026-04-21')]).toBe(37)
  })

  it('takes the thresholds’ unit from meta.units, the request’s otherwise', () => {
    const body = {
      meta: { ...chancesAnswer.meta, units: { threshold: '°C', chance: '%' } },
      data: { threshold: [0], date: ['2026-04-01'], season: ['spring'], chance: [50] },
    } as unknown as TableResponse
    expect(freezeChances(body).unit).toBe('degC')
  })

  it('draws a line per threshold over the days the chances change, dashes telling them apart', () => {
    const option = freezeOddsOption({ chances, show: 'spring', today, units: us, palette })
    const series = seriesOf(option)
    expect(series.map((s) => s.name)).toEqual(['Frost (32 °F)', 'Hard freeze (28 °F)', 'Killing freeze (24 °F)'])
    expect(series.map((s) => s.lineStyle?.type)).toEqual(['solid', 'dashed', 'dotted'])
    const axis = (option as { xAxis: { data: string[] }[] }).xAxis[0].data
    expect(axis[0] > '2026-01-01' && axis.at(-1)! < '2026-07-01').toBe(true) // trimmed to spring's changes
    expect(series[0].data[0]).toBe(100)
    expect(series[0].data.at(-1)).toBe(0)
  })

  it('names thresholds in the reader’s units and draws only those asked for', () => {
    const option = freezeOddsOption({ chances, thresholds: [28], show: 'fall', today, units: metric, palette })
    expect(seriesOf(option).map((s) => s.name)).toEqual(['Hard freeze (−2.2 °C)'])
    const axis = (option as { xAxis: { data: string[] }[] }).xAxis[0].data
    expect(axis[0] >= '2026-07-01').toBe(true)
    expect(axis).toContain(today)
  })

  it('tables the chances by date for the season shown', () => {
    const rows = freezeOddsRows(chances, us, undefined, 'fall')
    expect(rows.columns[0]).toBe('Frost (32 °F) (%)')
    expect(rows.rows.every((r) => r.date >= '2026-07-01')).toBe(true)
  })

  it('reads the dates by threshold and probability', () => {
    expect(dates.probabilities).toEqual([10, 50, 90])
    expect(dates.rows[0]).toMatchObject({
      threshold: 32,
      fahrenheit: 32,
      lastSpring: { 10: '2026-04-06', 50: '2026-04-17', 90: '2026-05-03' },
      firstFall: { 10: '2026-10-03', 50: '2026-10-21', 90: '2026-11-09' },
      seasonDays: { 10: 161, 50: 186, 90: 216 },
      yearsSpring: 30,
      withoutSpring: 0,
    })
  })

  it('says the dates in words', () => {
    const text = freezeSummary({ dates, units: us })
    expect(text).toContain('Over the 30 years from 1996 to 2025:')
    expect(text).toContain(
      'Frost (32 °F): the last of spring came by Apr 17 in half the years, and after May 3 in 1 year in 10. The first of fall came by Oct 21 in half the years, and by Oct 3 in 1 year in 10. The season without a frost typically lasted 186 days (161 to 216 days in 8 years out of 10).',
    )
    expect(freezeSummary({ dates, units: metric, show: 'fall' })).toContain(
      'Killing freeze (−4.4 °C): the first of fall came by Nov 18 in half the years',
    )
  })

  it('says when no year had a freeze', () => {
    const none = { ...dates, rows: [{ ...dates.rows[0], withoutSpring: 30, withoutFall: 30 }] }
    expect(freezeSummary({ dates: none, units: us })).toContain('No year had a spring frost. No year had a fall frost.')
  })
})
