// The Degree days tab's pure parts, over answers recorded from the dev server (frontend/test/fixtures/site)
import { describe, expect, it } from 'vitest'

import { units as unitsFor } from '@/lib/units'
import ddAnswer from '@/test/fixtures/site/degree-days.json'
import presetsAnswer from '@/test/fixtures/site/presets.json'
import { testPalette as palette } from '@/test/palette'
import type { PresetInfo, TableResponse } from '@/types/api'

import {
  ddCsvRows,
  ddOption,
  ddQuery,
  ddRun,
  ddTable,
  ddWords,
  decodeTokens,
  defaultStart,
  parseSetting,
  resolveSeries,
  seriesName,
  seriesTotals,
  settingText,
} from './degreeDays'

const us = unitsFor('imperial')
const metric = unitsFor('metric')
const presets = presetsAnswer.data as PresetInfo[]
const body = ddAnswer as unknown as TableResponse
const today = '2026-11-25'
// The fixture: corn's setting (modified 50/86) and single sine 41/86 from May 13, 2026, projected to December 31
const series = resolveSeries(['corn', 'sine_41_86'], presets)

describe('settings', () => {
  it('names a setting as the API does, tenths of a degree with a p', () => {
    expect(settingText({ method: 'sine', base: 41, upper: 86 })).toBe('sine_41_86')
    expect(settingText({ method: 'average', base: 39.2, upper: null })).toBe('average_39p2')
    expect(settingText({ method: 'modified', base: 44.6000001, upper: 86 })).toBe('modified_44p6_86')
    expect(parseSetting('average_39_84p2')).toEqual({ method: 'average', base: 39, upper: 84.2 })
    expect(parseSetting('cubic_50')).toBeNull()
  })

  it('keeps three settings at most, each once, from the view', () => {
    expect(decodeTokens('corn;sine_41;corn;average_40;sine_50')).toEqual(['corn', 'sine_41', 'average_40'])
    expect(decodeTokens(null)).toEqual([])
  })

  it('reads presets by id and settings by text, dropping anything else and repeats', () => {
    const found = resolveSeries(['corn', 'no-such-crop', 'sine_41_86', 'modified_50_86'], presets)
    expect(found.map((s) => s.dd)).toEqual(['modified_50_86', 'sine_41_86'])
    expect(seriesName(found[0], us)).toBe('Corn (field)')
    expect(seriesName(found[1], us)).toBe('Single sine, base 41 °F, upper 86 °F')
    expect(seriesName(found[1], metric)).toBe('Single sine, base 5.0 °C, upper 30.0 °C')
  })
})

describe('when counting starts', () => {
  const planting = [{ crop: 'corn', typical: '05-13' }]

  it("takes a crop's typical planting date here, or the site's own", () => {
    expect(defaultStart({ from: 'planting', series, year: 2026, planting })).toEqual({
      date: '2026-05-13',
      reason: 'the typical corn (field) planting date here',
    })
    expect(defaultStart({ from: 'planting', series, year: 2026, planting, saved: '2026-05-02' }).date).toBe(
      '2026-05-02',
    )
    // A saved date in another year says nothing of this one
    expect(defaultStart({ from: 'planting', series, year: 2025, planting, saved: '2026-05-02' }).date).toBe(
      '2025-05-13',
    )
  })

  it("takes an insect's usual biofix, else May 1", () => {
    const cutworm = resolveSeries(['black-cutworm'], presets)
    expect(defaultStart({ from: 'biofix', series: cutworm, year: 2026 }).date).toBe('2026-05-01')
    const looper = resolveSeries(['cabbage-looper'], presets)
    expect(defaultStart({ from: 'biofix', series: looper, year: 2026 })).toEqual({
      date: '2026-07-15',
      reason: 'Cabbage looper’s usual biofix',
    })
    expect(defaultStart({ from: 'jan1', series, year: 2026 }).date).toBe('2026-01-01')
  })

  it('asks for every setting in one request, in °F, with the projection only this year', () => {
    const query = ddQuery({
      lat: 44.12,
      lng: -89.52,
      series,
      start: '2026-05-13',
      year: 2026,
      thisYear: 2026,
      projection: true,
    })
    expect(query).toEqual({
      lat: 44.12,
      lng: -89.52,
      dd: ['modified_50_86', 'sine_41_86'],
      start: '2026-05-13',
      end: null,
      projection: true,
      units: 'us',
    })
    const past = ddQuery({
      lat: 44.12,
      lng: -89.52,
      series,
      start: '2025-05-13',
      year: 2025,
      thisYear: 2026,
      projection: true,
    })
    expect(past).toMatchObject({ end: '2025-12-31', projection: null })
  })
})

describe('the answer', () => {
  const run = ddRun(body, series)

  it('has each day, the projection after the forecast', () => {
    expect(run.series).toHaveLength(2)
    expect(run.projected).toBe(true)
    expect(run.table.days[0].date).toBe('2026-05-13')
    expect(run.table.days.at(-1)).toMatchObject({ date: '2026-12-31', kind: 'projection' })
  })

  it("flags a day's degree days estimated when its temperatures were", () => {
    const columns = body.data as Record<string, unknown[]>
    const flagged = { ...body, data: { ...columns, temperature_estimated: columns.date.map((_, i) => i === 3) } }
    const days = ddRun(flagged as TableResponse, series).table.days
    expect([...days[3].estimated].sort()).toEqual([
      'dd_modified_50_86',
      'dd_modified_50_86_cum',
      'dd_sine_41_86',
      'dd_sine_41_86_cum',
    ])
    expect(days[2].estimated.size).toBe(0)
    const totals = seriesTotals(ddRun(flagged as TableResponse, series), today)
    expect(totals.map((t) => t.estimated)).toEqual([1, 1])
    expect(
      ddWords({
        run: ddRun(flagged as TableResponse, series),
        units: us,
        today,
        from: 'planting',
        start: '2026-05-13',
      }),
    ).toContain('Includes 1 estimated day.')
  })

  it('gives each total to date, at the forecast’s end and projected, in words', () => {
    const [corn] = seriesTotals(run, today)
    expect(corn.now?.date).toBe(today)
    expect(corn.forecast?.date).toBe('2026-12-05')
    expect(corn.projected?.date).toBe('2026-12-31')
    const words = ddWords({ run, units: us, today, from: 'planting', start: '2026-05-13' })
    expect(words).toMatch(/^Counted from planting on May 13, 2026\. Corn \(field\): 2,7\d\d °F·d through Nov 25; /)
    expect(words).toContain('by Dec 31 on past years’ weather (likely')
    // Degree days convert with the reader's units: °C·d are 5/9 of °F·d
    const value = corn.now!.value!
    expect(ddWords({ run, units: metric, today, from: 'jan1', start: '2026-05-13' })).toContain(
      `${Math.round((value * 5) / 9).toLocaleString('en-US')} °C·d through Nov 25`,
    )
  })

  it('charts daily bars above the running totals, the projection dashed over its band', () => {
    const option = ddOption({ run, units: us, palette, today }) as {
      series: { id: string; type: string; xAxisIndex: number; lineStyle?: { type: string } }[]
    }
    const ids = option.series.map((s) => s.id)
    expect(ids).toContain('daily-modified_50_86')
    expect(ids).toContain('total-sine_41_86')
    expect(option.series.find((s) => s.id === 'daily-modified_50_86')).toMatchObject({ type: 'bar', xAxisIndex: 0 })
    expect(option.series.find((s) => s.id === 'projection-modified_50_86')?.lineStyle?.type).toBe('dashed')
    expect(ids).toContain('band-projection-modified_50_86-upper')
  })

  it('tables its days newest first and writes them as CSV in the reader’s units', () => {
    const table = ddTable(run, us)
    expect(table.columns).toEqual([
      'Corn (field), daily (°F·d)',
      'Corn (field), total (°F·d)',
      'Single sine, base 41 °F, upper 86 °F, daily (°F·d)',
      'Single sine, base 41 °F, upper 86 °F, total (°F·d)',
    ])
    expect(table.rows[0]).toMatchObject({ date: '2026-12-31', forecast: true })
    expect(table.rows[0].values[1]).toMatch(/ \(projected\)$/)
    const csv = ddCsvRows(run, metric)
    expect(csv[0]).toEqual([
      'Date',
      'Kind',
      'Corn (field), daily (°C·d)',
      'Corn (field), total (°C·d)',
      'Corn (field), total P10 (°C·d)',
      'Corn (field), total P90 (°C·d)',
      'Single sine, base 5.0 °C, upper 30.0 °C, daily (°C·d)',
      'Single sine, base 5.0 °C, upper 30.0 °C, total (°C·d)',
      'Single sine, base 5.0 °C, upper 30.0 °C, total P10 (°C·d)',
      'Single sine, base 5.0 °C, upper 30.0 °C, total P90 (°C·d)',
      'Temperatures estimated',
    ])
    expect(csv[1].slice(0, 2)).toEqual(['2026-05-13', 'observed'])
  })
})
